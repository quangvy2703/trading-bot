"""So giay "BTC sap → cat chan MUA cua dong luong" — CHI GHI, khong dat lenh.

Dac ta: docs/btc-sap-pp1.md. Luat viet TRUOC khi so nay chay (03/11/2026) va
KHONG doi trong khi do:
  * Kich hoat: ngay UTC vua dong co BTC close / close hom truoc − 1 ≤ −5%.
  * Luat gia: dong MOI vi the MUA cua dong luong (xsmom) o gia close ngay do,
    va khong mo lenh mua dong luong moi trong 7 luot chay (ke ca luot kich
    hoat). Kich hoat lai trong luc dang chan thi keo dai them 7 luot.
  * RSI(2), TSVW, DSRM va chan BAN cua dong luong KHONG bi dung toi.
So nay khong doi gi trong bot: no doc so vi the cua chinh bot (positions) va
ghi lai, voi tung vi the bi luat dung toi, phan chenh USD giua "bot that" va
"bot co luat":
  'cắt'   vi the mua dang giu luc kich hoat → luat dong o close ngay kich hoat.
  'bỏ qua' vi the mua bot mo trong luc chan → luat khong mo.
Mot dong ket thuc khi bot that dong vi the do, hoac o luot dau tien SAU khi het
chan ma so cua vi the do den luot tai can bang (luc ay bot co luat se mo lai
neu van duoc chon — hai the gioi trung nhau tu do). Phi 10 bps khu hoi tinh
nhu engine backtest (mot lan moi vong): 'cắt' ma bot van giu den luc het chan
ton them 10 bps (dong roi mo lai); 'bỏ qua' ma bot dong trong luc chan tiet
kiem 10 bps. Funding bo qua.
"""
from __future__ import annotations

import time

from . import db, runner, settings
from . import strategies as ST
from .config import FEE_BPS

DAY = 86_400_000
X_DROP = 0.05
COOL = 7
# Backtest 2021-04 → 2026-10 (scripts: scratch btpkg/run_crash.py, o ngay 5% / 7):
# 77 lan kich hoat, chan dong luong +237 USD voi 1R = 2 USD → +118 R, sut 212 → 188 USD.
BACKTEST = {"triggers": 77, "years": 5.5, "pp1_usd": 237.0, "r_usd": 2.0, "pp1_r": 118.5,
            "r_per_trigger": 1.54, "ci_dsharpe": [-0.27, 0.58]}

SCHEMA = """
CREATE TABLE IF NOT EXISTS crash_event(
  id INTEGER PRIMARY KEY AUTOINCREMENT, t_day INTEGER UNIQUE, btc_ret REAL,
  t_run INTEGER, block_end INTEGER, late INTEGER DEFAULT 0, mode TEXT);
CREATE TABLE IF NOT EXISTS crash_row(
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER, pos_id INTEGER UNIQUE,
  kind TEXT, symbol TEXT, sleeve INTEGER, qty REAL, notional REAL, r_usd REAL,
  entry_px REAL, ref_px REAL, ref_day INTEGER, end_px REAL, end_ts INTEGER,
  end_why TEXT, d_usd REAL, open INTEGER DEFAULT 1);
"""


def init() -> None:
    with db.tx() as cx:
        cx.executescript(SCHEMA)


def _closes(cx, sym: str) -> dict:
    now = int(time.time() * 1000)
    return {int(r["ts"]): float(r["c"]) for r in cx.execute(
        "SELECT ts, c FROM bars WHERE symbol=? AND ts + ? <= ? ORDER BY ts", (sym, DAY, now))}


def _px(cx, sym: str, day: int):
    r = cx.execute("SELECT c FROM bars WHERE symbol=? AND ts=?", (sym, day)).fetchone()
    return float(r["c"]) if r else None


def _qty(p) -> float:
    q = p["qty"]
    if q:
        return float(q)
    n = p["notional"] or 0.0
    return float(n) / float(p["entry_px"]) if p["entry_px"] else 0.0


def run_once() -> dict:
    """Goi SAU luot chay ngay cua bot (so vi the da cap nhat)."""
    init()
    m = runner.mode()
    st = {"t": int(time.time() * 1000), "mode": m, "triggers": 0, "cut": 0, "skipped": 0, "ended": 0}
    _, X = settings.strat()
    epoch = db.kv_get("xsmom_epoch")
    cx = db.connect()
    try:
        btc = _closes(cx, "BTCUSDT")
        days = sorted(btc)
        if len(days) < 2:
            return st
        day = days[-1]
        last = int(db.kv_get("crash_last_day") or day - DAY)
        run = cx.execute("SELECT ts FROM runs WHERE status='xong' ORDER BY id DESC LIMIT 1").fetchone()
        run_ts = int(run["ts"]) if run else st["t"]
        new_ev = []
        for d in days:
            if d <= last or d - DAY not in btc:
                continue
            ret = btc[d] / btc[d - DAY] - 1
            if ret <= -X_DROP:
                new_ev.append((d, ret))
        pos_all = [dict(r) for r in cx.execute(
            "SELECT * FROM positions WHERE mode=? AND strategy='xsmom' AND side=1", (m,))]
        tracked = {int(r["pos_id"]) for r in cx.execute("SELECT pos_id FROM crash_row")}
        ev = cx.execute("SELECT * FROM crash_event WHERE mode=? ORDER BY t_day DESC LIMIT 1", (m,)).fetchone()
        ev = dict(ev) if ev else None
    finally:
        cx.close()

    msgs = []          # db.log lay khoa ghi — goi SAU khi tx dong, khong thi treo
    with db.tx() as cx:
        for d, ret in new_ev:
            late = int(d < day)
            # keo dai chan neu dang chan
            cur = cx.execute(
                "INSERT OR IGNORE INTO crash_event(t_day, btc_ret, t_run, block_end, late, mode) VALUES(?,?,?,?,?,?)",
                (d, ret, run_ts, d + (COOL - 1) * DAY, late, m))
            if not cur.rowcount:
                continue
            st["triggers"] += 1
            ev = dict(cx.execute("SELECT * FROM crash_event WHERE t_day=?", (d,)).fetchone())
            msgs.append(f"BTC sập {ret * 100:.1f}% ngày {time.strftime('%Y-%m-%d', time.gmtime(d / 1000))}"
                           f" · sổ giấy: cắt chân mua động lượng, chặn mua đến hết "
                           f"{time.strftime('%Y-%m-%d', time.gmtime((d + (COOL - 1) * DAY) / 1000))}"
                           + (" (phát hiện trễ)" if late else ""))
            # vi the mua dang giu TRUOC luot kich hoat → 'cắt' o close ngay d
            for p in pos_all:
                if p["id"] in tracked or not p["open"] or (p["entry_ts"] or 0) >= run_ts:
                    continue
                px = _px(cx, p["symbol"], d)
                if px is None:
                    continue
                cx.execute("INSERT OR IGNORE INTO crash_row(event_id,pos_id,kind,symbol,sleeve,qty,notional,r_usd,"
                           "entry_px,ref_px,ref_day) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (ev["id"], p["id"], "cắt", p["symbol"], p["sleeve"], _qty(p), p["notional"],
                            p["r_usd"], p["entry_px"], px, d))
                tracked.add(p["id"]); st["cut"] += 1
        # vi the mua bot mo trong luc chan → 'bỏ qua'. Luot cua ngay da dong D
        # chay luc D + 1 ngay + vai phut, nen luot chan cuoi (D = block_end) ket
        # thuc truoc block_end + 2 ngay.
        if ev:
            for p in pos_all:
                t_ = p["entry_ts"] or 0
                if p["id"] in tracked or t_ < ev["t_run"] or t_ >= ev["block_end"] + 2 * DAY:
                    continue
                cx.execute("INSERT OR IGNORE INTO crash_row(event_id,pos_id,kind,symbol,sleeve,qty,notional,r_usd,"
                           "entry_px,ref_px,ref_day) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (ev["id"], p["id"], "bỏ qua", p["symbol"], p["sleeve"], _qty(p), p["notional"],
                            p["r_usd"], p["entry_px"], p["entry_px"], day))
                tracked.add(p["id"]); st["skipped"] += 1
        # ket thuc cac dong dang mo
        byid = {p["id"]: p for p in pos_all}
        sl_today = ST.xsmom_sleeve_of(day, int(epoch)) if epoch is not None else None
        for r in [dict(x) for x in cx.execute("SELECT * FROM crash_row WHERE open=1")]:
            p = byid.get(r["pos_id"])
            be = cx.execute("SELECT MAX(block_end) FROM crash_event WHERE mode=?", (m,)).fetchone()[0] or 0
            fee = (r["notional"] or 0.0) * FEE_BPS / 1e4
            if p is not None and not p["open"]:
                end_px, why, extra = float(p["exit_px"]), "bot đóng", (fee if r["kind"] == "bỏ qua" else 0.0)
                end_ts = p["exit_ts"]
            elif day > be and sl_today is not None and p is not None and p["sleeve"] == sl_today:
                end_px = _px(cx, r["symbol"], day)
                if end_px is None:
                    continue
                why, extra, end_ts = "hết chặn · sổ tới lượt", (-fee if r["kind"] == "cắt" else 0.0), day + DAY
            else:
                continue
            q = r["qty"] or 0.0
            if r["kind"] == "cắt":
                d_usd = q * (r["ref_px"] - end_px) + extra          # luat ra som o ref_px
            else:
                d_usd = -q * (end_px - r["entry_px"]) + extra       # luat khong mo
            cx.execute("UPDATE crash_row SET end_px=?, end_ts=?, end_why=?, d_usd=?, open=0 WHERE id=?",
                       (end_px, end_ts, why, d_usd, r["id"]))
            st["ended"] += 1
    for x in msgs:
        db.log("warn", x)
    db.kv_set("crash_last_day", day)
    db.kv_set("crash_status", st)
    return st


def summary() -> dict:
    init()
    m = runner.mode()
    cx = db.connect()
    try:
        evs = [dict(r) for r in cx.execute("SELECT * FROM crash_event WHERE mode=? ORDER BY t_day DESC", (m,))]
        ids = [e["id"] for e in evs] or [-1]
        q = ",".join("?" * len(ids))
        rows = [dict(r) for r in cx.execute(f"SELECT * FROM crash_row WHERE event_id IN ({q}) ORDER BY id DESC", ids)]
        lastp = {}
        for r in rows:
            if r["open"]:
                lastp[r["symbol"]] = lastp.get(r["symbol"]) or cx.execute(
                    "SELECT c FROM bars WHERE symbol=? ORDER BY ts DESC LIMIT 1", (r["symbol"],)).fetchone()
    finally:
        cx.close()
    done = [r for r in rows if not r["open"] and r["d_usd"] is not None]
    usd = sum(r["d_usd"] for r in done)
    rr = sum(r["d_usd"] / r["r_usd"] for r in done if r["r_usd"])
    for r in rows:                       # tam tinh cho dong dang mo
        if r["open"] and lastp.get(r["symbol"]):
            px = float(lastp[r["symbol"]]["c"])
            r["d_now"] = (r["qty"] or 0) * ((r["ref_px"] - px) if r["kind"] == "cắt" else -(px - r["entry_px"]))
    blocking = bool(evs) and max(e["block_end"] for e in evs) >= int(db.kv_get("crash_last_day") or 0)
    return {"status": db.kv_get("crash_status", {}) or {}, "events": evs, "rows": rows, "mode": m,
            "rule": {"drop": X_DROP, "cool": COOL}, "blocking": blocking,
            "stats": {"events": len(evs), "rows": len(rows), "done": len(done), "usd": usd, "r": rr,
                      "r_per_event": rr / len(evs) if evs else None},
            "backtest": BACKTEST}
