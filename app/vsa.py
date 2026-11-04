"""VSA 4H — "day qua vung cung" roi nen giam khoi luong thap. PP6 cua bot.

Tom Williams, *Master the Markets* (VSA). Nghien cuu: scripts/gh_vsa.py,
gh_vsa_verify.py, gh_vsa_corr.py; dac ta: docs/vsa-push-4h.md. Day la o duy
nhat trong 324 o VSA song qua kiem do ben, nhung duoc chon SAU khi nhin luoi.

Hai phan trong tep nay, cung mot lich 4H (main._vsa_job):
  A. SO GIAY (VSA_PAPER): ghi doc lap, co lenh co dinh VSA_PAPER_USD — doi
     chieu khop ly tuong voi backtest. Khong dat lenh.
  B. CHIEN LUOC THAT PP6 (he so ALLOC_VSA / tab «Cấu hình» alloc_vsa, 0 = tat),
     dua vao bot 04/11/2026 theo yeu cau van hanh — TRUOC moc ">= 300 lenh
     giay" trong docs. Vi the ghi vao bang positions (strategy 'vsa'), luot
     ngay 00:05 giu nguyen chung; chi lich 4H mo / dong. Xem trade().

Moi 4 gio (00:02, 04:02, … UTC, ngay sau khi nen 4H dong), voi moi ma top N
thanh khoan (hang ngay da dong, nhu bot chinh):
  tin hieu o nen vua dong i (dinh nghia y het gh_vsa.feats, ho L7 PUSH + nen bg):
    * trong 10 nen truoc co nen "day qua vung cung": nen tang, bien do > 1,5×
      TB 30 nen, KL > 1,5× TB 30 nen, dong o 1/3 tren, close vuot dinh 20 nen;
    * trong 20 nen truoc co dau hieu manh: nen giam KL cao dong >= giua,
      hoac nen rong cham day 20 nen KL cao dong >= 0,6;
    * nen i giam (close < close truoc) va KL nho hon CA HAI nen truoc.
  → mua o open nen i+1, ra o close nen i+3 (giu 3 nen = 12 gio). Mot lenh
  mot ma mot luc. Phi 10 bps khu hoi + funding thuc (long tra).
Luot chay tre hon 15 phut sau open nen vao thi ghi "bỏ lỡ", khong vao — gia
open da qua, vao luc do khong con la phep thu cua backtest.
"""
from __future__ import annotations

import json
import time

import numpy as np

from . import data, db, delist as DL, executor, runner, settings
from .binance import PublicApi, Trader
from .config import CFG, FEE_BPS

H4 = 4 * 3_600_000
DAY = 86_400_000
HOLD = 3
LATE_MS = 15 * 60_000
NBARS = 150
NAME = "vsa"
EXIT_WHY = "VSA: bán ở close nến 4H thứ 3"


def _sh(x, k):
    out = np.full(len(x), np.nan if x.dtype.kind == "f" else False, dtype=x.dtype)
    out[k:] = x[:-k]
    return out


def _sma(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        cs = np.concatenate(([0.0], np.cumsum(x)))
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def _rollmax(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def _recent(m, k):
    cs = np.concatenate(([0], np.cumsum(m.astype(int))))
    i = np.arange(len(m))
    return (cs[i] - cs[np.maximum(i - k, 0)]) > 0


def signal(o, h, l, c, v) -> tuple[np.ndarray, dict]:
    """Mat na tin hieu cho moi nen + chi tiet cua nen cuoi. Giong gh_vsa.feats."""
    sp = h - l
    with np.errstate(invalid="ignore", divide="ignore"):
        vavg, ravg = _sh(_sma(v, 30), 1), _sh(_sma(sp, 30), 1)
        c1 = _sh(c, 1)
        v1, v2 = _sh(v, 1), _sh(v, 2)
        up, dn = c > c1, c < c1
        pos = np.where(sp > 0, (c - l) / np.where(sp > 0, sp, 1), 0.5)
        hiV = v > 1.5 * vavg
        lowV = (v < v1) & (v < v2)
        wide = sp > 1.5 * ravg
        hh20, ll20 = _sh(_rollmax(h, 20, np.max), 1), _sh(_rollmax(l, 20, np.min), 1)
        push = up & wide & hiV & (pos >= 0.67) & (c > hh20)
        sc = wide & (l <= ll20) & hiV & (pos >= 0.6)
        bg = _recent((dn & hiV & (pos >= 0.5)) | sc, 20)
        sig = _recent(push, 10) & dn & lowV & bg
    sig = np.nan_to_num(sig).astype(bool)
    i = len(c) - 1
    k = np.flatnonzero(push[max(0, i - 10):i])
    det = {"vol_x": float(v[i] / vavg[i]) if np.isfinite(vavg[i]) and vavg[i] > 0 else None,
           "push_bars_ago": int(10 - k[-1]) if len(k) else None}
    return sig, det


def _klines(api: PublicApi, sym: str) -> np.ndarray:
    k = api._get("/fapi/v1/klines", symbol=sym, interval="4h", limit=NBARS)
    return np.array([[float(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])]
                     for x in k])


def _funding_bps(api: PublicApi, sym: str, t0: int, t1: int) -> float:
    try:
        f = api.funding(sym, start_ms=t0, limit=100)
    except Exception:
        return 0.0
    return sum(float(x["fundingRate"]) for x in f if t0 <= int(x["fundingTime"]) < t1) * 1e4


def _top(n: int) -> list[str]:
    """Top n thanh khoan — tinh mot lan moi ngay (doc ca kho nen 1D ton vai giay)."""
    d = int(time.time() * 1000) // DAY
    c = db.kv_get("vsa_top", {}) or {}
    if c.get("day") == d and c.get("n") == n and c.get("syms"):
        return c["syms"]
    syms = runner.top_symbols(n)
    if syms:
        db.kv_set("vsa_top", {"day": d, "n": n, "syms": syms})
    return syms


def _open_rows() -> list:
    cx = db.connect()
    try:
        return [dict(r) for r in cx.execute("SELECT * FROM vsa_paper WHERE open=1")]
    finally:
        cx.close()


def run_once() -> dict:
    """Mot lich 4H: tai nen mot lan, ghi so giay (A) roi chay chien luoc that (B)."""
    now = int(time.time() * 1000)
    api = PublicApi()
    try:
        syms = _top(CFG.vsa_topn)
        held = {r["symbol"]: r for r in _open_rows()} if CFG.vsa_paper else {}
        live_held = [p["symbol"] for p in _book(runner.mode())]
        K, errs = {}, []
        for sym in sorted(set(syms) | set(held) | set(live_held)):
            try:
                K[sym] = _klines(api, sym)
            except Exception as e:
                errs.append(f"{sym}: {e}")
        st = _paper(api, K, syms, held, now, errs) if CFG.vsa_paper else {}
        try:
            trade(api, K, syms)
        except Exception as e:
            db.log("error", f"PP6 VSA 4H: lượt chạy thật/sổ bot lỗi: {e}")
            db.kv_set("vsa_live", {**(db.kv_get("vsa_live", {}) or {}), "t": now, "error": str(e)[:300]})
        return st
    finally:
        api.close()


def _paper(api: PublicApi, K: dict, syms: list, held: dict, now: int, errs: list) -> dict:
    st = {"t": now, "scanned": 0, "signals": 0, "opened": 0, "missed": 0, "closed": 0, "errors": list(errs)}
    try:
        for sym in sorted(set(syms) | set(held)):
            k = K.get(sym)
            if k is None:
                continue
            if len(k) < 80:
                continue
            t = k[:, 0].astype(np.int64)
            closed = t + H4 <= now
            # ---- dong lenh da du 3 nen
            r = held.get(sym)
            if r is not None:
                tx_bar = r["t_entry"] + (HOLD - 1) * H4
                j = np.flatnonzero((t == tx_bar) & closed)
                stale = now > tx_bar + H4 + DAY
                if len(j) or stale:
                    xi = int(j[0]) if len(j) else int(np.flatnonzero(closed)[-1])
                    px = float(k[xi, 4])
                    fund = _funding_bps(api, sym, r["t_entry"], r["t_entry"] + HOLD * H4)
                    bps = (px / r["entry_px"] - 1) * 1e4 - FEE_BPS - fund
                    with db.tx() as cx:
                        cx.execute("UPDATE vsa_paper SET open=0, t_exit=?, exit_px=?, fund_bps=?, bps=?, usd=?, why=?"
                                   " WHERE id=?", (int(t[xi]) + H4, px, fund, bps, CFG.vsa_paper_usd * bps / 1e4,
                                                   "giữ 3 nến" if len(j) else "thiếu nến — đóng ở nến cuối", r["id"]))
                    st["closed"] += 1
                    db.log("info", f"VSA 4H {sym}: sổ giấy đóng {px:g} · {bps:+.0f} bps")
                    held.pop(sym)
            if sym not in syms:
                continue
            # ---- tin hieu o nen vua dong
            ci = np.flatnonzero(closed)
            if not len(ci):
                continue
            i = int(ci[-1])
            st["scanned"] += 1
            sig, det = signal(k[:i + 1, 1], k[:i + 1, 2], k[:i + 1, 3], k[:i + 1, 4], k[:i + 1, 5])
            if not sig[-1] or sym in held:
                continue
            st["signals"] += 1
            t_sig, t_en = int(t[i]), int(t[i]) + H4
            if i + 1 < len(k) and int(t[i + 1]) == t_en and now - t_en <= LATE_MS:
                px, why, op = float(k[i + 1, 1]), None, 1
                st["opened"] += 1
                db.log("info", f"VSA 4H {sym}: sổ giấy MUA {px:g} (đẩy qua vùng cung {det['push_bars_ago']} nến trước,"
                               f" KL {det['vol_x']:.2f}× TB)" if det["vol_x"] else f"VSA 4H {sym}: sổ giấy MUA {px:g}")
            else:
                px, why, op = None, f"bỏ lỡ (chạy trễ {(now - t_en) / 60000:.0f} phút)", 0
                st["missed"] += 1
            with db.tx() as cx:
                cx.execute("INSERT OR IGNORE INTO vsa_paper(symbol, t_signal, t_entry, entry_px, why, detail, open)"
                           " VALUES(?,?,?,?,?,?,?)", (sym, t_sig, t_en, px, why, json.dumps(det), op))
    finally:
        db.kv_set("vsa_status", st)
    return st


def summary() -> dict:
    cx = db.connect()
    try:
        rows = [dict(r) for r in cx.execute("SELECT * FROM vsa_paper ORDER BY t_signal DESC LIMIT 300")]
        done = [r[0] for r in cx.execute("SELECT bps FROM vsa_paper WHERE open=0 AND bps IS NOT NULL")]
        usd = cx.execute("SELECT COALESCE(SUM(usd),0) FROM vsa_paper WHERE open=0 AND usd IS NOT NULL").fetchone()[0]
        missed = cx.execute("SELECT COUNT(*) FROM vsa_paper WHERE entry_px IS NULL").fetchone()[0]
    finally:
        cx.close()
    v = np.array(done, float)
    stats = {"n": len(v), "mean": float(v.mean()) if len(v) else None,
             "median": float(np.median(v)) if len(v) else None,
             "win": float((v > 0).mean()) if len(v) else None, "usd": float(usd), "missed": int(missed)}
    return {"status": db.kv_get("vsa_status", {}) or {}, "rows": rows, "stats": stats,
            "bot": live_summary(runner.mode()), "paper_on": CFG.vsa_paper,
            "usd_per_trade": CFG.vsa_paper_usd, "topn": CFG.vsa_topn,
            "backtest": {"n": 3594, "mean": 38.7, "median": -6.9, "win": 0.49, "per_day": 1.8}}


# ================================================================ B. chien luoc that PP6
def r_usd() -> float:
    return float(settings.risk()["r_usd"]) * float(settings.alloc().get(NAME, 0.0))


def _book(m: str) -> list:
    return [p for p in runner.open_positions(m) if p["strategy"] == NAME]


def _order_row(cx, a: dict, side: str, qty: float, nt: float, m: str, status: str, px: float, note: str) -> None:
    cx.execute("INSERT INTO orders(run_id,ts,strategy,sleeve,symbol,action,side,qty,notional,mode,status,px,resp)"
               " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (None, int(time.time() * 1000), NAME, None, a["symbol"], a["action"], side, qty, nt, m,
                status, px, note[:900]))


def trade(api: PublicApi, K: dict, syms: list) -> dict:
    """PP6 trong so cua bot (che do hien hanh: giay hoac that).

    DONG: vi the 'vsa' ma nen thu 3 (entry_ts + 2 nen) da dong → ban o gia
    thi truong (that) / close nen do (giay). MO: tin hieu o nen vua dong, chay
    trong 15 phut sau open nen vao → mua thi truong (that) / open nen (giay).
    Bo ma: bot dang giu ma do o PP6, dang giu chieu BAN o chien luoc khac (san
    mot chieu), hoac co thong bao huy niem yet. Tran: VSA_MAX_OPEN + apply_caps.
    Lai/lo da chot cong vao `vsa_realised:<mode>`, luot ngay ke tiep cong vao von.
    Chay trong RUN_LOCK: khong chong len luot ngay hay «ep lenh»."""
    m = runner.mode()
    r = r_usd()
    st = {"t": int(time.time() * 1000), "mode": m, "r_usd": r, "opened": 0, "closed": 0,
          "signals": 0, "missed": 0, "skipped": [], "blocked": [], "errors": []}
    if r <= 0 and not _book(m):
        db.kv_set("vsa_live", {**st, "off": True})
        return st
    if not runner.RUN_LOCK.acquire(timeout=600):
        db.log("warn", "PP6 VSA: lượt ngày giữ khoá quá 10 phút — bỏ lượt 4H này")
        return st
    trader = None
    try:
        live = m == "live"
        if live:
            ready, why = executor.live_ready()
            if not ready:
                raise RuntimeError(f"không đủ điều kiện chạy thật: {why}")
            trader = Trader()
        filt = data.filters(api) if live else {}
        prices = api.prices()
        eq = runner.equity_now()
        now = int(time.time() * 1000)
        realised = 0.0

        # ---- DONG: giu du 3 nen
        for p in _book(m):
            tx_bar = int(p["entry_ts"]) + (HOLD - 1) * H4
            if now < tx_bar + H4:
                continue
            k = K.get(p["symbol"])
            ref = None
            if k is not None:
                t = k[:, 0].astype(np.int64)
                j = np.flatnonzero((t == tx_bar) & (t + H4 <= now))
                if len(j):
                    ref = float(k[int(j[0]), 4])
            ref = ref or prices.get(p["symbol"])
            if not ref:
                st["errors"].append(f"{p['symbol']}: không có giá để đóng")
                continue
            a = {"action": "CLOSE", "symbol": p["symbol"]}
            px, qty, note = float(ref), float(p["qty"] or 0), "giấy"
            if live:
                try:
                    o = trader.market_order(p["symbol"], "SELL", qty, reduce_only=True)
                    px = float(o.get("avgPrice") or 0) or float(prices.get(p["symbol"]) or ref)
                    note = json.dumps({"orderId": o.get("orderId"), "status": o.get("status")})
                except Exception as e:
                    st["errors"].append(f"{p['symbol']}: bán lỗi {e}")
                    db.log("error", f"PP6 VSA {p['symbol']}: lệnh bán đóng vị thế lỗi: {e}")
                    with db.tx() as cx:
                        _order_row(cx, a, "SELL", qty, p["notional"] or 0, m, "lỗi", ref, str(e))
                    continue
            bps = (px - p["entry_px"]) / p["entry_px"] * 1e4 - FEE_BPS
            usd = float(p["notional"] or 0) * bps / 1e4
            realised += usd
            with db.tx() as cx:
                cx.execute("UPDATE positions SET open=0, exit_px=?, exit_ts=?, exit_why=?, pnl_bps=? WHERE id=?",
                           (px, now, EXIT_WHY, bps, p["id"]))
                _order_row(cx, a, "SELL", qty, p["notional"] or 0, m, "khớp", px, note)
            st["closed"] += 1
            db.log("info", f"PP6 VSA {p['symbol']}: bán {px:g} sau 3 nến 4H · {bps:+.0f} bps · {usd:+.2f} USD")

        # ---- MO: tin hieu o nen vua dong
        if r > 0:
            book = runner.open_positions(m)
            mine = {p["symbol"] for p in book if p["strategy"] == NAME}
            short = {p["symbol"] for p in book if p["side"] < 0}
            try:
                nob = DL.banned(DL.notices(), now, settings.risk()["ban_days"])
            except Exception:
                nob = {}
            R = settings.risk()
            acts = []
            for sym in syms:
                k = K.get(sym)
                if k is None or len(k) < 80:
                    continue
                t = k[:, 0].astype(np.int64)
                ci = np.flatnonzero(t + H4 <= now)
                if not len(ci):
                    continue
                i = int(ci[-1])
                sig, det = signal(k[:i + 1, 1], k[:i + 1, 2], k[:i + 1, 3], k[:i + 1, 4], k[:i + 1, 5])
                if not sig[-1]:
                    continue
                st["signals"] += 1
                t_en = int(t[i]) + H4
                if not (i + 1 < len(k) and int(t[i + 1]) == t_en and now - t_en <= LATE_MS):
                    st["missed"] += 1
                    db.log("warn", f"PP6 VSA {sym}: bỏ lỡ tín hiệu (chạy trễ {(now - t_en) / 60000:.0f} phút)")
                    continue
                why = ("bot đang giữ PP6" if sym in mine else "đang giữ chiều BÁN (sàn một chiều)" if sym in short
                       else "chặn mua (huỷ niêm yết)" if sym in nob else None)
                if why:
                    st["skipped"].append(f"{sym}: {why}")
                    continue
                nt, r_use = r / CFG.vsa_r_frac, r
                if R["order"] > 0 and nt > R["order"]:
                    nt = R["order"]
                    r_use = nt * CFG.vsa_r_frac
                acts.append({"action": "OPEN", "strategy": NAME, "sleeve": None, "symbol": sym, "side": 1,
                             "notional": nt, "r_usd": r_use, "t_en": t_en, "open_px": float(k[i + 1, 1]),
                             "why": f"VSA 4H MUA · đẩy qua vùng cung {det['push_bars_ago']} nến trước"
                                    + (f" · KL {det['vol_x']:.2f}× TB" if det["vol_x"] else "")})
            room = max(0, int(CFG.vsa_max_open) - len(mine))
            for a in acts[room:]:
                st["blocked"].append(f"{a['symbol']}: đã đủ {CFG.vsa_max_open} lệnh PP6 cùng lúc")
            ok, blocked = executor.apply_caps(acts[:room], eq + realised, prices, len(book),
                                              sum(float(p.get("notional") or 0.0) for p in book))
            st["blocked"] += [f"{b['symbol']}: {b['why']}" for b in blocked]
            held_ex = {x["symbol"]: x for x in trader.positions()} if live else {}
            for a in ok:
                sym = a["symbol"]
                ref = float(prices.get(sym) or a["open_px"])
                qty, px, note = a["notional"] / a["open_px"], a["open_px"], "giấy"
                if live:
                    f = filt.get(sym, {})
                    qty = executor.round_qty(a["notional"] / ref, f)
                    if qty <= 0 or qty < f.get("minq", 0) or qty * ref < f.get("minn", 5):
                        st["skipped"].append(f"{sym}: khối lượng dưới mức tối thiểu của sàn")
                        continue
                    executor.ensure_margin(trader, sym, held_ex)
                    try:
                        o = trader.market_order(sym, "BUY", qty)
                    except Exception as e:
                        st["errors"].append(f"{sym}: mua lỗi {e}")
                        db.log("error", f"PP6 VSA {sym}: lệnh mua lỗi: {e}")
                        with db.tx() as cx:
                            _order_row(cx, a, "BUY", qty, qty * ref, m, "lỗi", ref, str(e))
                        continue
                    qty = float(o.get("executedQty") or 0) or qty
                    px = float(o.get("avgPrice") or 0) or ref
                    note = json.dumps({"orderId": o.get("orderId"), "status": o.get("status")})
                nt = qty * px
                with db.tx() as cx:
                    cx.execute("INSERT INTO positions(strategy,sleeve,symbol,side,qty,weight,notional,r_usd,"
                               "entry_px,entry_ts,stop,tp,mode,open) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                               (NAME, None, sym, 1, qty, None, nt, a["r_usd"] * nt / a["notional"], px,
                                a["t_en"], None, None, m))
                    _order_row(cx, a, "BUY", qty, nt, m, "khớp", px, note)
                st["opened"] += 1
                db.log("info", f"PP6 {a['why']} · {sym} {px:g} · {nt:.0f} USD")
            if live and ok:
                try:
                    executor.fix_isolated(trader)
                except Exception as e:
                    db.log("error", f"PP6 VSA: rà ký quỹ isolated lỗi: {e}")
        if realised:
            key = f"vsa_realised:{m}"
            db.kv_set(key, float(db.kv_get(key, 0) or 0) + realised)
        st["realised"] = realised
        if live and (st["opened"] or st["closed"]):
            runner.safety_now(filt)
    finally:
        if trader is not None:
            trader.close()
        runner.RUN_LOCK.release()
        db.kv_set("vsa_live", st)
    return st


def live_summary(m: str) -> dict:
    cx = db.connect()
    try:
        op = [dict(r) for r in cx.execute(
            "SELECT symbol, entry_ts, entry_px, qty, notional FROM positions WHERE strategy=? AND mode=? AND open=1"
            " ORDER BY entry_ts DESC", (NAME, m))]
        cl = [dict(r) for r in cx.execute(
            "SELECT symbol, entry_ts, exit_ts, entry_px, exit_px, notional, pnl_bps FROM positions"
            " WHERE strategy=? AND mode=? AND open=0 ORDER BY exit_ts DESC LIMIT 300", (NAME, m))]
    finally:
        cx.close()
    usd = [(p["notional"] or 0) * (p["pnl_bps"] or 0) / 1e4 for p in cl]
    return {"mode": m, "open": op, "closed": cl, "n": len(cl), "usd": float(sum(usd)),
            "r_usd": r_usd(), "alloc": float(settings.alloc().get(NAME, 0.0)),
            "r_frac": CFG.vsa_r_frac, "max_open": CFG.vsa_max_open,
            "status": db.kv_get("vsa_live", {}) or {}}
