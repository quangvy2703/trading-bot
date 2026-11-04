"""C13 — lenh mua limit SAU duoi gia (接针 / richmanbtc ATR 指値, khung ngay).

Hai phan trong tep nay:
  A. CHIEN LUOC THAT cua bot (he so ALLOC_C13 / tab «Cấu hình» alloc_c13, 0 = tat):
     settle() o dau luot (truoc khi doc so vi the), place() o cuoi luot. Xem docs.
  B. SO GIAY (C13_PAPER): ghi doc lap, khong dat lenh — doi chieu khop ly tuong.

Nghien cuu 04/11/2026 (scratch qs2/t2_hour.py, docs/c13-limit-sau.md). Qua
5/5 luat nhung la chien luoc NGAY SAP: 86% R den tu 42 ngay sap toan thi
truong, ngay 10/10/2025 −43,7R. Nen chi ghi so giay, KHONG BAO GIO dat lenh.

Moi luot chay ngay (sau khi nen D dong), voi moi ma top N thanh khoan cua D:
  * dat lenh GIA: mua limit L = close_D − k × ATR14_D (ATR Wilder), co hieu luc
    trong nen D+1. 1R = 2 × ATR (gia), co lenh = C13_R_USD / 1R.
  * o luot sau (nen D+1 da dong): low_{D+1} ≤ L → khop o min(open_{D+1}, L),
    ban o close_{D+1}. Khong khop → huy. Phi 10 bps khu hoi, funding bo qua.
Ghi them ban "ngan sach theo ngay": ca ngay dung chung 1R (moi lenh khop
nhan 1/so lenh khop), vi ngay sap co the khop 50 lenh mot luc.
"""
from __future__ import annotations

import time

import numpy as np

from . import db, executor, settings, strategies as ST
from .binance import DAY, Trader
from .config import CFG, FEE_BPS

NAME = "c13"
EXIT_WHY = "C13: bán ở close ngày khớp"

SCHEMA = """
CREATE TABLE IF NOT EXISTS c13_paper(
  id INTEGER PRIMARY KEY AUTOINCREMENT, day_set INTEGER, symbol TEXT, rank INTEGER,
  close_ref REAL, atr REAL, lim REAL, qty REAL, r_usd REAL,
  status TEXT DEFAULT 'chờ', fill_px REAL, exit_px REAL, usd REAL, r REAL,
  UNIQUE(day_set, symbol));
CREATE TABLE IF NOT EXISTS c13_order(
  id INTEGER PRIMARY KEY AUTOINCREMENT, mode TEXT, day_set INTEGER, symbol TEXT, rank INTEGER,
  close_ref REAL, atr REAL, lim REAL, qty REAL, notional REAL, r_usd REAL, order_id TEXT,
  status TEXT DEFAULT 'chờ', filled REAL, avg_px REAL, pos_id INTEGER, ts INTEGER, note TEXT,
  UNIQUE(mode, day_set, symbol));
"""


def init() -> None:
    with db.tx() as cx:
        cx.executescript(SCHEMA)


def _atr_wilder(h, l, c, n=14) -> np.ndarray:
    pc = np.r_[np.nan, c[:-1]]
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    v = np.nanmean(tr[1:n + 1])
    out[n] = v
    for j in range(n + 1, len(c)):
        v = (v * (n - 1) + tr[j]) / n
        out[j] = v
    return out


def run_once(P: dict, day: int) -> dict:
    """Goi SAU luot chay ngay. P = ST.prep(bars) cua luot do, day = nen vua dong."""
    init()
    st = {"t": int(time.time() * 1000), "day": int(day), "settled": 0, "filled": 0, "placed": 0}
    cx = db.connect()
    try:
        pend = [dict(r) for r in cx.execute("SELECT * FROM c13_paper WHERE status='chờ'")]
    finally:
        cx.close()
    fee = FEE_BPS / 1e4
    upd = []
    for r in pend:
        d = P.get(r["symbol"])
        nxt = r["day_set"] + DAY
        if nxt > day:
            continue                      # nen khop chua dong
        j = None if d is None else int(np.searchsorted(d["t"], nxt))
        if d is None or j >= len(d["t"]) or d["t"][j] != nxt:
            upd.append(("không có nến", None, None, None, None, r["id"]))
            continue
        lo, op, cl = float(d["l"][j]), float(d["o"][j]), float(d["c"][j])
        if lo <= r["lim"]:
            e = min(op, r["lim"])
            usd = r["qty"] * (cl - e) - r["qty"] * e * fee
            upd.append(("khớp", e, cl, usd, usd / r["r_usd"] if r["r_usd"] else None, r["id"]))
            st["filled"] += 1
        else:
            upd.append(("không khớp", None, None, None, None, r["id"]))
        st["settled"] += 1
    rank = ST.ranks_on(P, day)
    new = []
    for sym, rk in rank.items():
        if rk > CFG.c13_topn:
            continue
        d = P[sym]
        j = int(np.searchsorted(d["t"], day))
        if j >= len(d["t"]) or d["t"][j] != day:
            continue
        a = _atr_wilder(d["h"][:j + 1], d["l"][:j + 1], d["c"][:j + 1])[j]
        c = float(d["c"][j])
        if not (np.isfinite(a) and a > 0 and c > 0):
            continue
        lim = c - CFG.c13_k * a
        if lim <= 0:
            continue
        one_r = 2.0 * a                   # 1R theo gia, nhu nghien cuu
        new.append((int(day), sym, int(rk), c, float(a), float(lim), CFG.c13_r_usd / one_r, CFG.c13_r_usd))
    with db.tx() as cx:
        cx.executemany("UPDATE c13_paper SET status=?, fill_px=?, exit_px=?, usd=?, r=? WHERE id=?", upd)
        cur = cx.executemany("INSERT OR IGNORE INTO c13_paper(day_set,symbol,rank,close_ref,atr,lim,qty,r_usd)"
                             " VALUES(?,?,?,?,?,?,?,?)", new)
        st["placed"] = cur.rowcount if cur.rowcount is not None else len(new)
    db.kv_set("c13_status", st)
    if st["filled"]:
        db.log("info", f"sổ giấy C13: {st['filled']} lệnh limit sâu khớp hôm nay")
    return st


def summary() -> dict:
    init()
    cx = db.connect()
    try:
        rows = [dict(r) for r in cx.execute(
            "SELECT * FROM c13_paper WHERE status='khớp' ORDER BY day_set DESC, symbol LIMIT 300")]
        allf = [dict(r) for r in cx.execute("SELECT day_set, usd, r FROM c13_paper WHERE status='khớp'")]
        n_set = cx.execute("SELECT COUNT(*) FROM c13_paper").fetchone()[0]
        pend = cx.execute("SELECT COUNT(*) FROM c13_paper WHERE status='chờ'").fetchone()[0]
    finally:
        cx.close()
    by = {}
    for r in allf:
        by.setdefault(r["day_set"], []).append(r)
    days = []
    for dset, rs in sorted(by.items(), reverse=True):
        usd = sum(x["usd"] for x in rs)
        days.append({"day": dset + DAY, "fills": len(rs), "usd": usd, "usd_budget": usd / len(rs),
                     "r": sum(x["r"] or 0 for x in rs)})
    rr = np.array([x["r"] for x in allf if x["r"] is not None], float)
    return {"status": db.kv_get("c13_status", {}) or {}, "rows": rows, "days": days[:120],
            "stats": {"orders": int(n_set), "pending": int(pend), "fills": len(allf),
                      "usd": float(sum(x["usd"] for x in allf)),
                      "usd_budget": float(sum(d["usd_budget"] for d in days)),
                      "r_per_fill": float(rr.mean()) if len(rr) else None,
                      "win": float((rr > 0).mean()) if len(rr) else None, "fill_days": len(days)},
            "rule": {"k": CFG.c13_k, "topn": CFG.c13_topn, "r_usd": CFG.c13_r_usd},
            "backtest": {"fills": 1568, "years": 5.5, "r_per_fill": 0.186, "win": 0.72, "fill_days": 227,
                         "crash_days_share_r": 0.86, "worst_day_r": -43.7}}



# ================================================================ A. chien luoc that
def r_usd() -> float:
    return float(settings.risk()["r_usd"]) * float(settings.alloc().get("c13", 0.0))


def settle(m: str, P: dict, day: int) -> dict:
    """Dau luot: lenh limit dat o luot truoc (co hieu luc trong nen day_set + 1)
    → khop thi ghi so thanh vi the 'c13' (luot nay se dong no o gia hien tai =
    close nen vua dong), khong khop thi huy. Che do that hoi san trang thai lenh."""
    init()
    st = {"filled": 0, "none": 0, "err": 0}
    cx = db.connect()
    try:
        pend = [dict(r) for r in cx.execute(
            "SELECT * FROM c13_order WHERE mode=? AND status='chờ' AND day_set + ? <= ?",
            (m, DAY, int(day)))]
    finally:
        cx.close()
    if not pend:
        return st
    trader = Trader() if m == "live" else None
    try:
        for r in pend:
            filled, avg, note = 0.0, None, ""
            if m == "live":
                try:
                    o = trader.order_status(r["symbol"], r["order_id"])
                    if o.get("status") in ("NEW", "PARTIALLY_FILLED"):
                        try:
                            trader.cancel_order(r["symbol"], r["order_id"])
                        except Exception as e:
                            note = f"huỷ lỗi: {str(e)[:120]}"
                        o = trader.order_status(r["symbol"], r["order_id"])
                    filled = float(o.get("executedQty") or 0)
                    avg = float(o.get("avgPrice") or 0) or None
                    note = note or str(o.get("status"))
                except Exception as e:
                    st["err"] += 1
                    db.log("error", f"C13 {r['symbol']}: không đọc được lệnh {r['order_id']}: {e}")
                    continue
            else:
                d = P.get(r["symbol"])
                nxt = r["day_set"] + DAY
                j = None if d is None else int(np.searchsorted(d["t"], nxt))
                if d is not None and j < len(d["t"]) and d["t"][j] == nxt and float(d["l"][j]) <= r["lim"]:
                    filled, avg = float(r["qty"]), min(float(d["o"][j]), float(r["lim"]))
                note = "giấy"
            with db.tx() as cx:
                pid = None
                if filled > 0 and avg:
                    cur = cx.execute(
                        "INSERT INTO positions(strategy,sleeve,symbol,side,qty,weight,notional,r_usd,"
                        "entry_px,entry_ts,stop,tp,mode,open) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                        (NAME, None, r["symbol"], 1, filled, None, filled * avg,
                         r["r_usd"] * filled / r["qty"] if r["qty"] else r["r_usd"], avg,
                         int(r["day_set"] + DAY), None, None, m))
                    pid = cur.lastrowid
                    st["filled"] += 1
                else:
                    st["none"] += 1
                cx.execute("UPDATE c13_order SET status=?, filled=?, avg_px=?, pos_id=?, note=? WHERE id=?",
                           ("khớp" if pid else "không khớp", filled, avg, pid, note, r["id"]))
    finally:
        if trader is not None:
            trader.close()
    if st["filled"]:
        db.log("info", f"C13: {st['filled']} lệnh limit sâu đã khớp — đóng ở lượt này")
    return st


def exits(cur: list) -> dict:
    """Moi vi the C13 dang mo deu dong o luot nay (giu dung mot ngay)."""
    out = {}
    for p in cur:
        if p.get("strategy") == NAME:
            p["exit_why"] = EXIT_WHY
            out[id(p)] = EXIT_WHY
    return out


def place(m: str, P: dict, day: int, rank: dict, eq: float, nobuy: dict, filt: dict) -> dict:
    """Cuoi luot: dat lenh limit mua cho nen ke tiep. Bo ma dang co vi the (san
    mot chieu: lenh mua khop se bu tru vi the ban), ma bi chan mua vi huy niem
    yet. Tran: so lenh, tong gia tri treo, va tran tong phoi nhiem cua bot."""
    init()
    st = {"placed": 0, "skip": 0, "budget": 0.0}
    r = r_usd()
    if r <= 0:
        return st
    K = settings.risk()
    cx = db.connect()
    try:
        held = {x["symbol"] for x in cx.execute("SELECT symbol FROM positions WHERE open=1 AND mode=?", (m,))}
        gross = float(cx.execute("SELECT COALESCE(SUM(notional),0) FROM positions WHERE open=1 AND mode=?",
                                 (m,)).fetchone()[0])
    finally:
        cx.close()
    budget = min(float(CFG.c13_max_gross_usd), float(K["gross_x"]) * float(eq) - gross)
    st["budget"] = budget
    if budget <= 0:
        db.log("warn", f"C13: không đặt lệnh — hết trần phơi nhiễm (đang {gross:.0f} USD)")
        return st
    cands = sorted((x for x in rank.items() if x[1] <= CFG.c13_topn), key=lambda x: x[1])
    rows, used = [], 0.0
    for sym, rk in cands:
        if sym in held or (nobuy and sym in nobuy):
            st["skip"] += 1
            continue
        d = P.get(sym)
        j = int(np.searchsorted(d["t"], day))
        if j >= len(d["t"]) or d["t"][j] != day:
            continue
        a = _atr_wilder(d["h"][:j + 1], d["l"][:j + 1], d["c"][:j + 1])[j]
        c = float(d["c"][j])
        if not (np.isfinite(a) and a > 0 and c > 0):
            continue
        lim = c - CFG.c13_k * a
        if lim <= 0:
            continue
        qty = r / (2.0 * a)
        nt = qty * lim
        if K["order"] > 0 and nt > K["order"]:
            qty, nt = K["order"] / lim, K["order"]
        if used + nt > budget or len(rows) >= CFG.c13_max_orders:
            break
        used += nt
        rows.append({"symbol": sym, "rank": int(rk), "close": c, "atr": float(a), "lim": float(lim),
                     "qty": qty, "nt": nt, "r": r * (nt / (r / (2.0 * a) * lim))})
    trader = Trader() if m == "live" else None
    try:
        held_ex = ({x["symbol"]: x for x in trader.positions()} if trader is not None else {})
        for x in rows:
            oid, note, qty, lim = None, "giấy", x["qty"], x["lim"]
            if trader is not None:
                f = filt.get(x["symbol"], {})
                qty = executor.round_qty(qty, f)
                if qty <= 0 or qty < f.get("minq", 0) or qty * lim < f.get("minn", 5):
                    st["skip"] += 1
                    continue
                px = executor._tick(lim, f, "BUY")
                executor.ensure_margin(trader, x["symbol"], held_ex)
                try:
                    o = trader.limit_gtd(x["symbol"], "BUY", qty, px, int(day) + 2 * DAY,
                                         f"c13-{x['symbol']}-{int(day) // DAY}"[:36])
                    oid, note, lim = str(o.get("orderId")), "đã treo", float(px)
                except Exception as e:
                    db.log("error", f"C13 {x['symbol']}: đặt limit lỗi: {e}")
                    st["skip"] += 1
                    continue
            with db.tx() as cx:
                cx.execute("INSERT OR IGNORE INTO c13_order(mode,day_set,symbol,rank,close_ref,atr,lim,qty,"
                           "notional,r_usd,order_id,status,ts,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (m, int(day), x["symbol"], x["rank"], x["close"], x["atr"], lim, qty, qty * lim,
                            x["r"], oid, "chờ", int(time.time() * 1000), note))
            st["placed"] += 1
    finally:
        if trader is not None:
            trader.close()
    db.kv_set("c13_live", {"t": int(time.time() * 1000), "mode": m, "day": int(day), **st})
    db.log("info", f"C13: treo {st['placed']} lệnh limit mua (close − {CFG.c13_k:g}×ATR), "
                   f"tổng ≈ {used:.0f} USD / trần {budget:.0f}")
    return st


def cancel_all(m: str) -> int:
    """Tat chien luoc: huy moi lenh dang treo (lenh da khop van duoc dong o luot sau).
    Thuc te gan nhu khong con gi: settle() da xu ly het lenh den han truoc do."""
    init()
    cx = db.connect()
    try:
        pend = [dict(r) for r in cx.execute("SELECT * FROM c13_order WHERE mode=? AND status='chờ'", (m,))]
    finally:
        cx.close()
    n = 0
    trader = Trader() if (m == "live" and pend) else None
    try:
        for r in pend:
            if trader is not None and r["order_id"]:
                try:
                    trader.cancel_order(r["symbol"], r["order_id"])
                except Exception:
                    pass
            n += 1
    finally:
        if trader is not None:
            trader.close()
    return n


def live_summary(m: str) -> dict:
    init()
    cx = db.connect()
    try:
        od = [dict(r) for r in cx.execute("SELECT * FROM c13_order WHERE mode=? ORDER BY id DESC LIMIT 400", (m,))]
        pos = [dict(r) for r in cx.execute(
            "SELECT entry_ts, exit_ts, entry_px, exit_px, qty, notional, r_usd, pnl_bps, symbol FROM positions "
            "WHERE strategy=? AND mode=? AND open=0 ORDER BY id DESC LIMIT 400", (NAME, m))]
    finally:
        cx.close()
    usd = [(p["notional"] or 0) * (p["pnl_bps"] or 0) / 1e4 for p in pos]
    return {"orders": od, "closed": pos, "usd": float(sum(usd)), "n": len(pos),
            "status": db.kv_get("c13_live", {}) or {}}
