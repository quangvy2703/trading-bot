"""Ung dung web + lich chay nen. Mot tien trinh, mot o dia, mot trang."""
from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import traceback
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from . import backtest, c13, crash, data, db, delist, executor, news, pp1tp, pp1wf, runner, settings, swingtp, vsa, vsbt as VB
from .binance import PublicApi, Trader
from .config import CFG, FEE_BPS

PAGE = Path(__file__).parent / "static" / "index.html"

# Hai ban dac ta da chot. Gan ./docs vao /docs CHI DOC trong compose, nen sua
# tai lieu la trang thay ngay, khong phai dung lai anh. Chay ngoai Docker (khong
# co /docs) thi doc thang docs/ cua repo.
DOCS_DIR = Path(os.environ.get("DOCS_DIR") or next(
    (p for p in (Path("/docs"), Path(__file__).parent.parent / "docs") if p.is_dir()),
    Path("/docs")))
DOCS = [("rsi2-connors", "RSI(2) Connors v3.1"),
        ("xsmom-volnorm", "Động lượng cắt ngang"),
        ("money-management-r", "Quản lý vốn theo R"),
        ("stop-dinh-day", "Cắt lỗ HVN · chốt lời"),
        ("huy-niem-yet", "Tin huỷ niêm yết"),
        ("vsa-push-4h", "PP6 · VSA 4H đẩy qua vùng cung"),
        ("btc-sap-pp1", "BTC sập → cắt chân mua (sổ giấy)"),
        ("pp1-kase-funding", "Động lượng: Kase + chặn bán (funding, BSADF)"),
        ("c13-limit-sau", "PP5 · C13 limit sâu 2 ATR")]
NAME_OK = re.compile(r"^[a-z0-9][a-z0-9.-]{0,63}$")
CONFIRM = "TÔI ĐỒNG Ý CHẠY THẬT"

app = FastAPI(title="Quản lý chạy thật", docs_url=None, redoc_url=None)
sched = BackgroundScheduler(timezone="UTC")


@app.on_event("startup")
def _start() -> None:
    db.init()
    if not db.kv_get("seeded"):
        # Gieo mam 1.500 tep mat vai phut; chan startup thi healthcheck fail
        # va Docker khoi dong lai vong vo tan. Day sang luong nen.
        def _seed():
            try:
                n = data.seed_from_npz()
                db.kv_set("seeded", {"files": n, "ts": int(time.time() * 1000)})
            except Exception as e:
                db.log("warn", f"gieo mầm lỗi: {e}")
        threading.Thread(target=_seed, daemon=True, name="seed").start()
    if not db.kv_get("seeded1h"):
        def _seed1h():
            try:
                n = data.seed_1h_from_npz()
                db.kv_set("seeded1h", {"files": n, "ts": int(time.time() * 1000)})
            except Exception as e:
                db.log("warn", f"gieo mầm nến 1H lỗi: {e}")
        threading.Thread(target=_seed1h, daemon=True, name="seed1h").start()
    # Thong bao huy niem yet + the Monitoring: gieo mot lan tu file da tai san
    # (mount /seedann), roi doc vai trang API moi nhat de bat kip phan con
    # thieu. Doc lai ca lich su qua API (~250 trang) bi Binance chan 429.
    def _ann():
        try:
            if not db.kv_get("ann_seeded"):
                n, m = delist.seed_from_cache(CFG.seed_ann_dir)
                if n or m:
                    db.kv_set("ann_seeded", {"delist": n, "monitor": m, "ts": int(time.time() * 1000)})
                    db.log("info", f"gieo mầm {n} thông báo huỷ niêm yết, {m} lượt thêm / bỏ thẻ Monitoring")
            n = delist.refresh(3)
            m = delist.refresh_monitor(5)
            db.log("info", f"cập nhật thông báo: {n} dòng huỷ niêm yết, {m} dòng thẻ Monitoring")
        except Exception as e:
            db.log("warn", f"nạp thông báo huỷ niêm yết / thẻ Monitoring lỗi: {e}")
    threading.Thread(target=_ann, daemon=True, name="ann").start()
    if CFG.news_paper:
        threading.Thread(target=news.run, daemon=True, name="news").start()
    if executor.live_ready()[0]:
        # Vi the isolated thieu ky quy, hay thieu dung an toan tren san, khong
        # doi duoc toi luot chay ke tiep.
        def _margin():
            t = None
            try:
                t = Trader()
                executor.fix_isolated(t)
            except Exception as e:
                db.log("error", f"rà ký quỹ isolated lúc khởi động lỗi: {e}")
            finally:
                if t is not None:
                    t.close()
            runner.safety_now()
        threading.Thread(target=_margin, daemon=True, name="margin").start()
    # Vi the nguoi dung tu cat tren Binance: doi chieu moi 5 phut de trang
    # quan li khop san, khong doi toi luot 00:05.
    sched.add_job(_sync, "interval", minutes=5, id="sync",
                  replace_existing=True, coalesce=True, max_instances=1)
    hh, _, mm = CFG.run_at_utc.partition(":")
    sched.add_job(_job, CronTrigger(hour=int(hh), minute=int(mm or 0)),
                  id="daily", replace_existing=True,
                  misfire_grace_time=3600, coalesce=True)
    # Nen 4H dong luc 00/04/08/12/16/20 UTC; chay 2 phut sau de Binance chot nen.
    # Luon dat lich: so giay VSA (VSA_PAPER) va PP6 that (alloc_vsa, bat/tat luc
    # chay o tab «Cấu hình») dung chung lich nay; ca hai tat thi lich khong lam gi.
    sched.add_job(_vsa_job, CronTrigger(hour="*/4", minute=2),
                  id="vsa4h", replace_existing=True,
                  misfire_grace_time=600, coalesce=True)
    # PP1 chot loi lenh BAN: nen 1H dong dau gio, chay phut 1 (sau khi Binance chot nen).
    sched.add_job(_tp_job, CronTrigger(minute=1),
                  id="pp1tp1h", replace_existing=True,
                  misfire_grace_time=900, coalesce=True)
    # PP1 windfall: nen 15m dong o phut 0/15/30/45, chay phut 1 sau do.
    sched.add_job(_wf_job, CronTrigger(minute="1,16,31,46"),
                  id="pp1wf15m", replace_existing=True,
                  misfire_grace_time=300, coalesce=True)
    sched.start()
    db.log("info", f"khởi động · lịch chạy {CFG.run_at_utc} UTC · "
                   f"chạy thật ở tầng mã: {'MỞ' if CFG.live_enabled_env else 'KHOÁ'}")


@app.on_event("shutdown")
def _stop() -> None:
    sched.shutdown(wait=False)


def _sync() -> None:
    if not executor.live_ready()[0]:
        return
    try:
        runner.reconcile_now()
    except Exception as e:
        db.log("error", f"đối chiếu sổ với sàn lỗi: {e}")


def _job() -> None:
    try:
        runner.run_once()
    except Exception:
        db.log("error", "lượt chạy theo lịch hỏng:\n" + traceback.format_exc()[-800:])
    _crash_job()


def _crash_job() -> None:
    """So giay BTC sap (app/crash.py) — doc so vi the SAU luot chay, khong dat lenh."""
    if not CFG.crash_paper:
        return
    try:
        crash.run_once()
    except Exception:
        db.log("error", "sổ giấy BTC sập hỏng:\n" + traceback.format_exc()[-800:])


def _vsa_job() -> None:
    try:
        vsa.run_once()
    except Exception:
        db.log("error", "lịch VSA 4H (PP6 + sổ giấy) hỏng:\n" + traceback.format_exc()[-800:])


def _tp_job() -> None:
    """PP1: chot loi lenh BAN moi gio (app/pp1tp.py, cong tac xsmom_tp)."""
    try:
        pp1tp.run_once()
    except Exception:
        db.log("error", "lịch chốt lời PP1 mỗi giờ hỏng:\n" + traceback.format_exc()[-800:])


def _wf_job() -> None:
    """PP1: windfall moi nen 15m (app/pp1wf.py, cong tac xsmom_wf);
    TSVW / DSRM: chot loi theo nen 15m (app/swingtp.py)."""
    try:
        pp1wf.run_once()
    except Exception:
        db.log("error", "lịch windfall PP1 15m hỏng:\n" + traceback.format_exc()[-800:])
    try:
        swingtp.run_once()
    except Exception:
        db.log("error", "lịch chốt lời TSVW/DSRM 15m hỏng:\n" + traceback.format_exc()[-800:])


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": int(time.time() * 1000)}


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE.read_text(encoding="utf-8")


def _rows(sql: str, *a) -> list:
    cx = db.connect()
    try:
        return [dict(r) for r in cx.execute(sql, a)]
    finally:
        cx.close()


@app.get("/api/docs")
def docs_list():
    """Cac tai lieu cho tab «Phương pháp»."""
    return [{"key": k, "title": t, "ok": (DOCS_DIR / f"{k}.md").is_file()}
            for k, t in DOCS]


@app.get("/api/docs/{key}")
def doc_one(key: str):
    # Khong ghep duong dan tu dau vao: chi nhan ten don, roi kiem ket qua
    # resolve van nam trong DOCS_DIR.
    if not NAME_OK.match(key):
        raise HTTPException(400, "tên tài liệu không hợp lệ")
    root = DOCS_DIR.resolve()
    p = (root / f"{key}.md").resolve()
    if root not in p.parents or not p.is_file():
        raise HTTPException(404, f"không có tài liệu «{key}» trong {DOCS_DIR}")
    title = next((t for k, t in DOCS if k == key), key)
    return {"key": key, "title": title, "file": p.name,
            "mtime": int(p.stat().st_mtime * 1000),
            "text": p.read_text(encoding="utf-8")}


@app.get("/api/flags")
def flags():
    """Ma bi gan co: tin go spot / go perp / the Monitoring — tab «Tin & cờ»."""
    return {"ban_days": settings.risk()["ban_days"], "now": int(time.time() * 1000),
            "rows": delist.flags(settings.risk()["ban_days"], int(time.time() * 1000))}


@app.get("/api/news")
def news_state():
    """So giay theo tin: trang thai nguon, do tre, lenh gia, tin gan day."""
    return news.summary()


@app.get("/api/crash")
def crash_state():
    """So giay BTC sap → cat chan mua dong luong: su kien, vi the bi dung, chenh USD."""
    return crash.summary()


@app.get("/api/c13")
def c13_state():
    """So giay C13 lenh limit sau (app/c13.py) — khong dat lenh."""
    return c13.summary()


@app.get("/api/vsa")
def vsa_state():
    """So giay VSA 4H: tin hieu, lenh gia, so voi backtest."""
    return vsa.summary()


# Chuoi lai/lo NGAY theo backtest cua tung phuong phap — tep tinh dung san bang
# scripts/build_methods_overview.py (repo nghien cuu). Don vi R voi he so 1;
# trang tu nhan theo 1R va he so dang chay.
OVERVIEW = Path(__file__).parent / "methods_bt.json"
_OV: dict = {"mtime": None, "v": None}


@app.get("/api/overview")
def overview():
    """Tab «Tổng quan»: backtest theo phuong phap + cau hinh dang chay + lai/lo
    thuc te theo thang (vi the da dong cua so hien hanh, ca PP6 VSA)."""
    if not OVERVIEW.is_file():
        raise HTTPException(404, f"thiếu tệp {OVERVIEW.name} — chạy build_methods_overview.py")
    mt = OVERVIEW.stat().st_mtime
    if _OV["mtime"] != mt:
        _OV.update(mtime=mt, v=json.loads(OVERVIEW.read_text(encoding="utf-8")))
    m = runner.mode()
    act: dict = {}

    def add(month: str, key: str, usd: float) -> None:
        x = act.setdefault(month, {}).setdefault(key, [0.0, 0, 0])
        x[0] += usd
        x[1] += 1
        x[2] += usd > 0

    ym = lambda ms: time.strftime("%Y-%m", time.gmtime(ms / 1000))
    for p in _rows("SELECT strategy, exit_ts, notional, pnl_bps FROM positions "
                   "WHERE open=0 AND mode=? AND exit_ts IS NOT NULL "
                   "AND pnl_bps IS NOT NULL", m):
        add(ym(p["exit_ts"]), p["strategy"], (p["notional"] or 0.0) * p["pnl_bps"] / 1e4)
    return {"bt": _OV["v"], "mode": m,
            "cfg": {"r_usd": settings.risk()["r_usd"], "equity": CFG.start_equity,
                    "equity_now": runner.equity_now(),
                    "alloc": settings.alloc(), "pp1x": settings.pp1x(),
                    "vsa_paper": CFG.vsa_paper, "vsa_usd": CFG.vsa_paper_usd, "vsa_r_frac": CFG.vsa_r_frac,
                    "crash_paper": CFG.crash_paper, "c13_paper": CFG.c13_paper, "caps": settings.risk()},
            "actual": act}


def _ov_bt() -> dict | None:
    if not OVERVIEW.is_file():
        return None
    mt = OVERVIEW.stat().st_mtime
    if _OV["mtime"] != mt:
        _OV.update(mtime=mt, v=json.loads(OVERVIEW.read_text(encoding="utf-8")))
    return _OV["v"]


VSBT_K = ("xsmom", "rsi2", "tsvw", "dsrm", "c13", "vsa")


@app.get("/api/vsbt")
def actual_vs_backtest():
    """Bang dieu khien: lenh THUC TE (vi the da dong cua che do hien hanh) so voi
    BACKTEST (methods_bt.json, cung nguon tab «Tổng quan») tung chien luoc.

    Backtest quy ve he so dang chay: USD/ngay = R/ngay × 1R × he so; so lenh/ngay,
    ti le thang, R TB/lenh lay tren toan giai doan 2021–26. Cua so thuc te: tu luot
    chay dau tien cua che do nay (hoac lenh dau tien) toi bay gio."""
    bt = _ov_bt()
    m = runner.mode()
    al, ru = settings.alloc(), float(settings.risk()["r_usd"])
    F = settings.pp1x()
    ck = ("k" if F["kase"] else "") + ("f" if F["fund_veto"] else "") + ("b" if F["bsadf_veto"] else "")
    ckc = ck + ("+tp" if F.get("tp") else "") + ("+wf" if F.get("wf") else "")   # khoa cache / vsbt: chuoi chot loi / windfall PP1
    first = _rows("SELECT MIN(ts) AS t FROM runs WHERE mode=?", m)[0]["t"]
    rows = _rows("SELECT strategy, entry_ts, exit_ts, notional, r_usd, pnl_bps FROM positions "
                 "WHERE mode=? AND open=0 AND pnl_bps IS NOT NULL", m)
    nopen = {r["strategy"]: r["n"] for r in _rows(
        "SELECT strategy, COUNT(*) AS n FROM positions WHERE mode=? AND open=1 GROUP BY strategy", m)}
    t0 = min([x for x in [first] + [r["entry_ts"] for r in rows] if x] or [int(time.time() * 1000)])
    days = max(0.0, (time.time() * 1000 - t0) / 86_400_000)
    out = {}
    for k in VSBT_K:
        rs = [r for r in rows if r["strategy"] == k]
        usd = [(r["notional"] or 0) * r["pnl_bps"] / 1e4 for r in rs]
        rr = [u / r["r_usd"] for u, r in zip(usd, rs) if r["r_usd"]]
        act = {"n": len(rs), "open": nopen.get(k, 0), "usd": float(sum(usd)),
               "win": (sum(u > 0 for u in usd) / len(usd)) if usd else None,
               "r_per": (sum(rr) / len(rr)) if rr else None,
               "bps": (sum(r["pnl_bps"] for r in rs) / len(rs)) if rs else None}
        b = None
        if bt and k in bt.get("series", {}):
            s = list(bt["series"][k])
            if k == "xsmom" and ck and ck in bt.get("pp1x_combo", {}):
                s = [a + c for a, c in zip(s, bt["pp1x_combo"][ck])]
            if k == "xsmom" and F.get("tp") and "pp1tp" in bt["series"]:
                s = [a + c for a, c in zip(s, bt["series"]["pp1tp"])]
            if k == "xsmom" and F.get("wf") and "pp1wf" in bt["series"]:
                s = [a + c for a, c in zip(s, bt["series"]["pp1wf"])]
            if k == "vsa":                 # tep luu USD cho lenh 100 USD → R (1R = gia di VSA_R_FRAC)
                s = [x / (100 * CFG.vsa_r_frac) for x in s]
            n_d = len(s)
            tr = bt.get("trades", {}).get(k) or []
            nt, nw = sum(x[0] for x in tr), sum(x[1] for x in tr)
            a = float(al.get(k, 0.0))
            mu_ = sum(s) / n_d
            sd_ = (sum((x - mu_) ** 2 for x in s) / n_d) ** 0.5 * ru * a
            b = {"per_day_usd": mu_ * ru * a, "trades_per_day": nt / n_d, "sd_day_usd": sd_,
                 "win": nw / nt if nt else None, "r_per": sum(s) / nt if nt else None,
                 "exp_n": nt / n_d * days, "exp_usd": sum(s) / n_d * ru * a * days}
        if b and days >= 1:
            act["per_year"] = act["usd"] / days * 365
            act["z"] = ((act["usd"] - b["exp_usd"]) / (b["sd_day_usd"] * days ** 0.5)) if b["sd_day_usd"] else None
        out[k] = {"alloc": float(al.get(k, 0.0)), "act": act, "bt": b}
    agg = None
    if bt and bt.get("gross"):
        n = bt["n"]; caps = settings.risk(); cap = float(caps["gross_x"]) * float(CFG.start_equity)
        d = [0.0] * n; g = [0.0] * n; npos = [0] * n
        for k in VSBT_K:
            a = float(al.get(k, 0.0))
            if a <= 0 or k not in bt["series"]:
                continue
            s_ = list(bt["series"][k])
            if k == "xsmom" and ck and ck in bt.get("pp1x_combo", {}):
                s_ = [x + c for x, c in zip(s_, bt["pp1x_combo"][ck])]
            if k == "xsmom" and F.get("tp") and "pp1tp" in bt["series"]:
                s_ = [x + c for x, c in zip(s_, bt["series"]["pp1tp"])]
            if k == "xsmom" and F.get("wf") and "pp1wf" in bt["series"]:
                s_ = [x + c for x, c in zip(s_, bt["series"]["pp1wf"])]
            if k == "vsa":
                s_ = [x / (100 * CFG.vsa_r_frac) for x in s_]
            G = bt["gross"].get(k) or [0.0] * n; NP = bt["npos"].get(k) or [0] * n
            for i in range(n):
                d[i] += s_[i] * ru * a; g[i] += G[i] * ru * a; npos[i] += NP[i]
        dc = [x * min(1.0, cap / gi) if gi > 0 else x for x, gi in zip(d, g)]

        def st(x):
            mu = sum(x) / n; sd = (sum((v - mu) ** 2 for v in x) / n) ** 0.5
            c = pk = dd = 0.0; mon = {}
            for i, v in enumerate(x):
                c += v; pk = max(pk, c); dd = max(dd, pk - c)
                mk = time.strftime("%Y-%m", time.gmtime((bt["start"] + i * 86_400_000) / 1000))
                mon[mk] = mon.get(mk, 0.0) + v
            return {"tot": c, "per_day": c / n, "sd_day": sd, "dd": dd, "pos": sum(v > 0 for v in mon.values()), "nm": len(mon)}
        q = lambda a, p: sorted(a)[min(len(a) - 1, int(p * len(a)))]
        tpd = sum((r["bt"] or {}).get("trades_per_day", 0) for k, r in out.items() if r["alloc"] > 0)
        agg = {"cap": st(dc), "raw": st(d), "npos_mean": sum(npos) / n, "npos_p95": q(npos, .95),
               "gross_p95": q(g, .95), "trades_per_day": tpd, "cap_usd": cap,
               "over": sum(gi > cap for gi in g) / n, "start_equity": CFG.start_equity}
    eqr = _rows("SELECT ts, value FROM equity WHERE mode=? ORDER BY ts", m)
    cmpx = None
    if bt and bt.get("r_stats"):
        vals = [float(r["value"]) for r in eqr]
        dx = [v - p for v, p in zip(vals, [float(CFG.start_equity)] + vals[:-1])]
        rr = _rows("SELECT gross, n_open FROM runs WHERE mode=? AND status='xong' ORDER BY ts", m)
        L = len(dx) if dx else max(1, int(round(days)))
        caps_ = settings.risk()
        key = (tuple(sorted(al.items())), ru, ckc, CFG.vsa_r_frac, float(caps_["gross_x"]) * float(CFG.start_equity), _OV["mtime"])
        cmpx = VB.compare(bt, key, al, ru, ckc, CFG.vsa_r_frac, key[4],
                          {"d": dx, "g": [float(r["gross"] or 0) for r in rr], "npos": [int(r["n_open"] or 0) for r in rr]},
                          L, {k: out[k]["act"] for k in out})
    e_now = runner.equity_now()
    total = {"closed_usd": float(sum(r["act"]["usd"] for r in out.values())),
             "mtm_usd": float(e_now - CFG.start_equity), "equity": e_now, "n_eq": len(eqr)}
    return {"mode": m, "since": t0, "days": days, "r_usd": ru, "rows": out, "agg": agg, "total": total, "cmp": cmpx,
            "bt_range": [bt["start"], bt["start"] + (bt["n"] - 1) * 86_400_000] if bt else None}


@app.get("/api/state")
def state():
    ready, why = executor.live_ready()
    m = runner.mode()
    nxt = sched.get_job("daily")
    cx = db.connect()
    try:
        nbars = cx.execute("SELECT COUNT(*) FROM bars").fetchone()[0]
        nsym = cx.execute("SELECT COUNT(DISTINCT symbol) FROM bars").fetchone()[0]
        last_bar = cx.execute("SELECT MAX(ts) FROM bars").fetchone()[0]
    finally:
        cx.close()
    return {
        "mode": m,
        "live": {"env_open": CFG.live_enabled_env, "armed": executor.live_armed(),
                 "has_keys": CFG.has_keys(), "ready": ready, "why": why,
                 "venue": CFG.binance_env},
        "caps": settings.risk(),
        "stream": CFG.stream(m),
        "fee_bps": FEE_BPS,
        "alloc": settings.alloc(),
        "params": dict(zip(("rsi2", "xsmom"), settings.strat())),
        "drift": settings.drift(),
        "data": {"bars": nbars, "symbols": nsym, "last_bar": last_bar,
                 "seeded": db.kv_get("seeded")},
        "sched": {"at": CFG.run_at_utc,
                  "next": nxt.next_run_time.isoformat() if nxt and nxt.next_run_time else None,
                  "vsa_next": (j.next_run_time.isoformat()
                               if (j := sched.get_job("vsa4h")) and j.next_run_time else None),
                  "pp1tp_next": (j2.next_run_time.isoformat()
                                 if (j2 := sched.get_job("pp1tp1h")) and j2.next_run_time else None),
                  "pp1tp_last": db.kv_get("pp1tp_last", {}) or {},
                  "pp1wf_next": (j3.next_run_time.isoformat()
                                 if (j3 := sched.get_job("pp1wf15m")) and j3.next_run_time else None),
                  "pp1wf_last": db.kv_get("pp1wf_last", {}) or {},
                  "pp1wf_reenter": db.kv_get("pp1wf_reenter", []) or []},
        "last_run": db.kv_get("last_run"),
        "safety": db.kv_get("safety", {}) or {},
        "blocked": db.kv_get("blocked"),
        "equity": _rows("SELECT ts, value FROM equity WHERE mode=? ORDER BY ts", m),
        "positions": [{**p, "exit_plan": runner.planned_exit(p)} for p in _rows(
            "SELECT * FROM positions WHERE open=1 AND mode=? "
            "ORDER BY strategy, sleeve, symbol", m)],
        "closed": _rows(
            "SELECT * FROM positions WHERE open=0 AND mode=? "
            "ORDER BY exit_ts DESC LIMIT 500", m),
        "orders": _rows("SELECT * FROM orders ORDER BY id DESC LIMIT 80"),
        "runs": _rows("SELECT * FROM runs ORDER BY id DESC LIMIT 20"),
        "events": _rows("SELECT * FROM events ORDER BY id DESC LIMIT 60"),
    }


_ACCT: dict = {"at": 0.0, "v": None}
_ACCT_LOCK = threading.Lock()


@app.get("/api/account")
def account():
    """Von THAT tren san: so du vi + lai/lo chua chot + vi the dang giu.

    Chi DOC, khong dat lenh, khong can cong tac chay that. Gom trong 5 giay
    de nhieu tab cung mo khong nhan len so lan goi khoa API. Tra kem vi the
    (so luong, gia vao) de trang tu tinh lai/lo chua chot theo gia danh dau
    song thay vi doi lan hoi ke tiep.
    """
    if not CFG.has_keys():
        return {"ok": False, "why": "chưa có khoá API"}
    with _ACCT_LOCK:
        if _ACCT["v"] is not None and time.time() - _ACCT["at"] < 5:
            return _ACCT["v"]
        t = None
        try:
            t = Trader()
            a = t.account()
            v = {"ok": True, "venue": CFG.binance_env,
                 "stream": CFG.stream("live"),
                 "wallet": float(a.get("totalWalletBalance", 0)),
                 "upnl": float(a.get("totalUnrealizedProfit", 0)),
                 "margin": float(a.get("totalMarginBalance", 0)),
                 "avail": float(a.get("availableBalance", 0)),
                 "positions": [
                     {"symbol": x["symbol"], "amt": float(x["positionAmt"]),
                      "entry": float(x["entryPrice"])}
                     for x in a.get("positions", [])
                     if float(x.get("positionAmt", 0) or 0)],
                 "ts": int(time.time() * 1000)}
            # Lenh dieu kien dang treo (dung lo / chot loi), ke ca lenh nguoi
            # dung tu dat hay tu chinh tren Binance. Loi o day khong lam hong
            # phan so du.
            try:
                v["stops"] = [
                    {"symbol": o["symbol"], "side": o.get("side"),
                     "type": o.get("orderType"),
                     "trigger": float(o.get("triggerPrice") or 0),
                     "close": o.get("closePosition") in (True, "true"),
                     "qty": float(o.get("quantity") or 0),
                     "bot": str(o.get("clientAlgoId", "")).startswith("sl-"),
                     "algoId": o.get("algoId")}
                    for o in t.open_algo_orders()]
            except Exception as e:
                v["stops"], v["stops_err"] = [], str(e)[:200]
        except Exception as e:
            why = str(e)
            ip = re.search(r"request ip: ([0-9a-fA-F.:]+)", why)
            if "-2015" in why:
                # Thuong gap nhat: khoa chua bat quyen Futures, hoac co danh
                # sach IP ma chua co IP ra ngoai cua may nay.
                why = ("Binance từ chối khoá API (-2015) — kiểm tra quyền "
                       "Futures và danh sách IP của khoá"
                       + (f"; IP máy này: {ip.group(1)}" if ip else ""))
            v = {"ok": False, "why": why[:200]}
        finally:
            if t is not None:
                t.close()
        _ACCT.update(at=time.time(), v=v)
        return v


@app.post("/api/preview")
def preview():
    """Tinh so muc tieu va viec can lam, KHONG dat bat ky lenh nao."""
    api = PublicApi()
    try:
        from . import strategies as ST
        bars = data.load_all(settings.strat()[0]["min_bars"])
        bars = {s: b for s, b in bars.items() if data.is_crypto(b)}
        P = ST.prep(bars)
        if not P:
            raise HTTPException(400, "kho nến rỗng — bấm «tải dữ liệu» trước")
        day = int(max(d["t"][-1] for d in P.values()))
        rank = ST.ranks_on(P, day)
        cur = runner.open_positions()
        target, note = runner.build_target(P, rank, day, cur)
        actions = executor.plan(target, cur)
        allowed, blocked = executor.apply_caps(
            actions, runner.equity_now(), api.prices(), len(cur),
            sum(float(p.get("notional") or 0.0) for p in cur))
        if runner.mode() == "live":     # dung thu tu nhu run_once
            allowed, clash = executor.one_way(allowed, cur)
            blocked += clash
        return {"day": day, "note": note, "target": target,
                "actions": allowed, "blocked": blocked,
                "equity": runner.equity_now()}
    finally:
        api.close()


@app.post("/api/run")
def run_now():
    try:
        out = runner.run_once()
    except Exception as e:
        raise HTTPException(500, str(e))
    _crash_job()
    return out


@app.post("/api/force")
def force(body: dict = Body(...)):
    """Ep vao mot lenh bi chan cua luot moi nhat — BO QUA tran rui ro."""
    try:
        return runner.force_blocked(int(body["i"]), int(body["run_id"]))
    except (KeyError, ValueError):
        raise HTTPException(400, "thiếu i / run_id")
    except RuntimeError as e:
        raise HTTPException(400, str(e))


@app.post("/api/reconcile")
def reconcile_api():
    """Doi chieu so voi san ngay: chot so vi the san da het."""
    if not executor.live_ready()[0]:
        raise HTTPException(400, "chỉ dùng khi đang chạy thật")
    return {"closed": runner.reconcile_now()}


@app.post("/api/fetch")
def fetch():
    api = PublicApi()
    try:
        syms = data.live_symbols(api)
        n = data.refresh(api, syms)
        top = runner.top_symbols(20)
        n1 = data.refresh_1h(api, top)
        return {"symbols": len(syms), "bars_added": n, "bars1h_added": n1, "top_1h": len(top)}
    finally:
        api.close()


@app.get("/api/config")
def get_config():
    return {"spec": {k: {"group": g, "type": t.__name__, "min": lo, "max": hi,
                         "desc": d}
                     for k, (g, t, lo, hi, d) in settings.SPEC.items()},
            "locked": settings.locked(), "effective": settings.effective(),
            "overrides": settings.overrides(), "drift": settings.drift(),
            "sched_at": CFG.run_at_utc}


@app.post("/api/config")
def set_config(body: dict = Body(...)):
    if body.get("reset"):
        settings.reset()
        return get_config()
    try:
        settings.save(body.get("patch") or {})
    except ValueError as e:
        raise HTTPException(400, str(e))
    return get_config()


@app.get("/api/backtest")
def backtest_meta():
    """Gia tri mac dinh cho tab tinh lich su = cau hinh dang chay."""
    return {"defaults": backtest.defaults(), "research": backtest.RESEARCH,
            "spec": {k: {"group": g, "type": t.__name__, "min": lo, "max": hi,
                         "desc": d}
                     for k, (g, t, lo, hi, d) in settings.SPEC.items()},
            "extra": {k: {"type": t.__name__, "min": lo, "max": hi, "desc": d}
                      for k, (t, lo, hi, d) in backtest.EXTRA.items()}}


@app.post("/api/backtest")
def backtest_run(body: dict = Body(default={})):
    """Tinh lai lich su voi bo tham so tuy chon. Khong doi cau hinh, khong dat lenh."""
    try:
        return backtest.run(body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(409, str(e))


@app.post("/api/testapi")
def test_api(body: dict = Body(default={})):
    """Thu ca duong ong dat lenh: ky API -> dat -> doc lai -> huy.

    KHONG dung lenh thi truong: no khop ngay va de lai vi the that. Dung
    lenh GIOI HAN dat o GIA BANG MOT NUA thi truong, tuc khong the khop,
    roi huy ngay trong `finally`. Neu no khop that thi bao dong to.

    Khong doi hoi cong tac chay that: muc dich la kiem khoa API TRUOC khi
    bat. Nhung no CO dat lenh len san, nen UI phai hoi lai truoc.
    """
    if not CFG.has_keys():
        raise HTTPException(400, "Chưa có BINANCE_API_KEY / BINANCE_API_SECRET.")
    sym = (body.get("symbol") or "BTCUSDT").upper()
    steps, t = [], Trader()
    api = PublicApi()
    oid = None
    try:
        steps.append({"b": "đọc tài khoản", "ok": True,
                      "d": f"số dư {t.balance()['total']:,.2f} USDT · "
                           f"khả dụng {t.balance()['avail']:,.2f}"})
        hedge = t.dual_side()
        steps.append({"b": "chế độ vị thế", "ok": not hedge,
                      "d": "hai chiều (Hedge) — mã này cần MỘT CHIỀU"
                           if hedge else "một chiều (one-way) — đúng yêu cầu"})
        f = data.filters(api).get(sym)
        if not f:
            raise HTTPException(400, f"sàn không có mã «{sym}»")
        px = api.prices().get(sym)
        if not px:
            raise HTTPException(400, f"không lấy được giá «{sym}»")
        # Gia bang MOT NUA thi truong -> lenh mua khong the khop.
        price = math.floor(px * 0.5 / f["tick"]) * f["tick"]
        price = round(price, f["pprec"])
        need = max(f["minn"] * 1.02, 1e-9) / price
        step = f["step"] or 0.001
        qty = math.ceil(max(need, f["minq"]) / step) * step
        qty = round(qty, max(0, int(round(-math.log10(step)))) if step < 1 else 0)
        steps.append({"b": "tính lệnh thử", "ok": True,
                      "d": f"MUA {qty} {sym} ở {price:,.{f['pprec']}f} "
                           f"= {qty*price:,.2f} USDT · giá thị trường "
                           f"{px:,.{f['pprec']}f} (lệnh cách 50%, không thể khớp)"})
        r = t.limit_order(sym, "BUY", qty, price)
        oid = r.get("orderId")
        steps.append({"b": "đặt lệnh", "ok": True,
                      "d": f"id {oid} · trạng thái {r.get('status')}"})
        st = t.order_status(sym, oid)
        filled = float(st.get("executedQty", 0) or 0)
        steps.append({"b": "đọc lại lệnh", "ok": filled == 0,
                      "d": f"trạng thái {st.get('status')} · đã khớp {filled}"
                           + (" ← BẤT THƯỜNG, lệnh lẽ ra không thể khớp"
                              if filled else "")})
        return {"ok": all(x["ok"] for x in steps), "symbol": sym,
                "venue": CFG.binance_env, "steps": steps}
    except HTTPException:
        raise
    except Exception as e:
        steps.append({"b": "LỖI", "ok": False, "d": str(e)[:300]})
        return {"ok": False, "symbol": sym, "venue": CFG.binance_env,
                "steps": steps}
    finally:
        if oid is not None:
            try:
                c = t.cancel_order(sym, oid)
                steps.append({"b": "huỷ lệnh", "ok": c.get("status") == "CANCELED",
                              "d": f"trạng thái {c.get('status')}"})
            except Exception as e:
                steps.append({"b": "huỷ lệnh", "ok": False,
                              "d": f"KHÔNG HUỶ ĐƯỢC — vào Binance huỷ tay "
                                   f"id {oid}: {str(e)[:200]}"})
        db.log("warn", f"thử API trên {sym} ({CFG.binance_env}): "
                       + " · ".join(f"{x['b']}={'ok' if x['ok'] else 'LỖI'}"
                                    for x in steps))
        t.close()
        api.close()


@app.post("/api/arm")
def arm(body: dict = Body(...)):
    """Khoa thu hai. Khoa thu nhat la bien moi truong, khong doi duoc tu day."""
    on = bool(body.get("on"))
    if on:
        if not CFG.live_enabled_env:
            raise HTTPException(
                400, "Tầng mã đang khoá: đặt LIVE_TRADING_ENABLED=1 trong "
                     "docker-compose.yml rồi dựng lại container.")
        if not CFG.has_keys():
            raise HTTPException(400, "Chưa có BINANCE_API_KEY / SECRET.")
        if (body.get("confirm") or "").strip() != CONFIRM:
            raise HTTPException(400, f"Gõ đúng câu xác nhận: «{CONFIRM}»")
        # Ma dat lenh theo che do MOT CHIEU. Kiem truoc khi bat, neu khong moi
        # lenh se chet voi -4061 va chi biet sau khi da den gio chay.
        t = Trader()
        try:
            hedge = t.dual_side()
        except Exception as e:
            raise HTTPException(
                400, f"Không đọc được chế độ vị thế của tài khoản: {e}")
        finally:
            t.close()
        if hedge:
            raise HTTPException(
                400, "Tài khoản đang ở chế độ HAI CHIỀU (Hedge). Mã đặt lệnh "
                     "theo chế độ MỘT CHIỀU — ở Hedge mọi lệnh bị từ chối "
                     "(-4061). Đổi ở Binance Futures → Preferences → "
                     "Position Mode → One-way, rồi bật lại.")
    db.kv_set("live_armed", on)
    db.log("warn" if on else "info",
           f"công tắc chạy thật: {'BẬT' if on else 'TẮT'} "
           f"(sàn {CFG.binance_env})")
    return {"armed": on}


@app.post("/api/flatten")
def flatten(body: dict = Body(default={})):
    """Dừng khẩn: tắt công tắc rồi đóng sạch vị thế đang mở."""
    db.kv_set("live_armed", False)
    m = runner.mode()
    cur = runner.open_positions(m)
    if not cur:
        db.log("warn", "dừng khẩn: không có vị thế nào đang mở")
        return {"closed": 0, "armed": False}
    api = PublicApi()
    try:
        prices = api.prices()
        filt = data.filters(api) if m == "live" else {}
        acts = [{"action": "CLOSE", **p} for p in cur]
        with db.tx() as cx:
            rid = cx.execute(
                "INSERT INTO runs(ts,bar_ts,mode,status,detail) VALUES(?,?,?,?,?)",
                (int(time.time() * 1000), 0, m, "dừng khẩn", "")).lastrowid
        done = executor.execute(rid, acts, runner.equity_now(), prices, filt, m)
        with db.tx() as cx:
            for a in done:
                cx.execute("UPDATE positions SET open=0, exit_px=?, exit_ts=?,"
                           " exit_why=? WHERE id=?",
                           (a["px"], int(time.time() * 1000), "dừng khẩn",
                            a["id"]))
        db.log("warn", f"dừng khẩn: đóng {len(done)} vị thế")
        return {"closed": len(done), "armed": False}
    finally:
        api.close()


@app.exception_handler(Exception)
def _err(_req, exc):
    db.log("error", f"{type(exc).__name__}: {exc}")
    return JSONResponse({"error": str(exc)}, status_code=500)
