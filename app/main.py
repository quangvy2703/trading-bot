"""Ung dung web + lich chay nen. Mot tien trinh, mot o dia, mot trang."""
from __future__ import annotations

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

from . import backtest, data, db, executor, runner, settings
from .binance import PublicApi, Trader
from .config import CFG, FEE_BPS

PAGE = Path(__file__).parent / "static" / "index.html"

# Hai ban dac ta da chot. Gan ../docs vao /docs CHI DOC trong compose, nen sua
# tai lieu la trang thay ngay, khong phai dung lai anh.
DOCS_DIR = Path(os.environ.get("DOCS_DIR", "/docs"))
DOCS = [("rsi2-connors", "RSI(2) Connors v3.1"),
        ("xsmom-volnorm", "Động lượng cắt ngang"),
        ("money-management-r", "Quản lý vốn theo R"),
        ("stop-dinh-day", "Cắt lỗ HVN · chốt lời")]
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
    if executor.live_ready()[0]:
        # Vi the isolated thieu ky quy khong doi duoc toi luot chay ke tiep.
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
        threading.Thread(target=_margin, daemon=True, name="margin").start()
    hh, _, mm = CFG.run_at_utc.partition(":")
    sched.add_job(_job, CronTrigger(hour=int(hh), minute=int(mm or 0)),
                  id="daily", replace_existing=True,
                  misfire_grace_time=3600, coalesce=True)
    sched.start()
    db.log("info", f"khởi động · lịch chạy {CFG.run_at_utc} UTC · "
                   f"chạy thật ở tầng mã: {'MỞ' if CFG.live_enabled_env else 'KHOÁ'}")


@app.on_event("shutdown")
def _stop() -> None:
    sched.shutdown(wait=False)


def _job() -> None:
    try:
        runner.run_once()
    except Exception:
        db.log("error", "lượt chạy theo lịch hỏng:\n" + traceback.format_exc()[-800:])


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
                  "next": nxt.next_run_time.isoformat() if nxt and nxt.next_run_time else None},
        "last_run": db.kv_get("last_run"),
        "equity": _rows("SELECT ts, value FROM equity WHERE mode=? ORDER BY ts", m),
        "positions": _rows(
            "SELECT * FROM positions WHERE open=1 AND mode=? "
            "ORDER BY strategy, sleeve, symbol", m),
        "closed": _rows(
            "SELECT * FROM positions WHERE open=0 AND mode=? "
            "ORDER BY exit_ts DESC LIMIT 60", m),
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
            actions, runner.equity_now(), api.prices(), len(cur))
        return {"day": day, "note": note, "target": target,
                "actions": allowed, "blocked": blocked,
                "equity": runner.equity_now()}
    finally:
        api.close()


@app.post("/api/run")
def run_now():
    try:
        return runner.run_once()
    except Exception as e:
        raise HTTPException(500, str(e))


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
    return {"defaults": backtest.defaults(),
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
