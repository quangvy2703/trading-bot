"""Tinh lai lai/lo da chot cua MOI vi the that da dong, tu so lieu that cua san.

Luc dong lenh, so ghi lai/lo theo cong thuc uoc luong: gia ra la gia luot chay
doc duoc (co khi lech gia khop), phi tru phang FEE_BPS, funding bo qua. Day la
nguon sai cua «lãi đã chốt» so voi Binance. Module nay dung lai tung vi the:

  gia vao / ra = gia khop TB cua dung lenh tren san (userTrades, gop theo orderId)
  phi          = phi that cua lenh vao + lenh ra, chia theo khoi luong cua vi the
  funding      = moi lan tra funding cua ma (income FUNDING_FEE), chia cho cac vi
                 the dang mo luc do theo khoi luong (mot chieu: cung chieu het)
  lai rong     = chieu × qty × (ra − vao) − phi + funding

Van tinh THEO TUNG VI THE (moi so mot lot), khong theo gia von TB cua san: tong
cac vi the da dong co the khac «Realized PnL» cua Binance khi ma con vi the mo
(san tinh lai theo gia von binh quan ca vi the rong). Dong het thi hai so gap nhau.

Ghi lai: entry_px, exit_px, exit_ts (gio khop that), pnl_bps (= lai rong / notional,
de moi cho dang cong notional × pnl_bps khong phai doi), fee_usd, fund_usd.
"""
from __future__ import annotations

import time
from collections import defaultdict

from . import db
from .binance import DAY, Trader

EPS = 1e-9


def _orders(fills: list) -> list:
    """Gop cac lan khop thanh lenh: [{id, side, qty, px, fee, t}] theo thoi gian."""
    g: dict = {}
    for x in fills:
        o = g.setdefault(x["orderId"], {"id": x["orderId"], "side": x["side"], "qty": 0.0,
                                        "cost": 0.0, "fee": 0.0, "t": 0})
        q = float(x["qty"])
        o["qty"] += q
        o["cost"] += q * float(x["price"])
        o["fee"] += float(x["commission"])          # commissionAsset USDT
        o["t"] = max(o["t"], int(x["time"]))
    out = sorted(g.values(), key=lambda o: o["t"])
    for o in out:
        o["px"] = o["cost"] / o["qty"] if o["qty"] else 0.0
        o["left"] = o["qty"]
    return out


def _pick(orders: list, side: str, qty: float, t: int, lo: int, hi: int, exact: bool):
    """Lenh `side` gan `t` nhat trong [t-lo, t+hi] con du khoi luong cho `qty`.
    exact: khoi luong lenh phai bang qty (lenh vao: moi lenh mot vi the)."""
    tol = EPS + 1e-6 * qty
    best = None
    for o in orders:
        if o["side"] != side or not (t - lo <= o["t"] <= t + hi) or o["left"] + tol < qty:
            continue
        if exact and abs(o["qty"] - qty) > tol:
            continue
        if best is None or abs(o["t"] - t) < abs(best["t"] - t):
            best = o
    return best


def attribute(pos: list, fills: dict, funding: dict) -> list:
    """Thuan tinh toan (khong goi san, khong ghi so) — de kiem tra duoc.

    pos: moi vi the that (ca dang mo — can de chia funding), fills: {ma: userTrades},
    funding: {ma: [(t, usd)]}. Tra [{id, ...so moi}] cho vi the DA DONG ghep duoc."""
    out = []
    by_sym = defaultdict(list)
    for p in pos:
        by_sym[p["symbol"]].append(p)
    for sym, ps in by_sym.items():
        od = _orders(fills.get(sym, []))
        m: dict = {}
        # vao truoc: lenh vao luon mot vi the mot lenh, khoi luong bang dung qty.
        # C13 la lenh limit sau khop trong ngay SAU entry_ts → cua so +36 gio.
        for p in sorted(ps, key=lambda p: p["entry_ts"]):
            sd = "BUY" if p["side"] > 0 else "SELL"
            o = _pick(od, sd, p["qty"], p["entry_ts"], 6 * 3600_000, 36 * 3600_000, True)
            if o:
                o["left"] -= p["qty"]
                m[p["id"]] = {"in": o}
        for p in sorted((p for p in ps if not p["open"]), key=lambda p: p["exit_ts"] or 0):
            if p["id"] not in m:
                continue
            sd = "SELL" if p["side"] > 0 else "BUY"
            # lenh ra co the dong nhieu vi the cung luc (dung an toan / dong tay)
            o = _pick(od, sd, p["qty"], int(p["exit_ts"] or 0), 6 * 3600_000, 10 * 60_000, False)
            if o:
                o["left"] -= p["qty"]
                m[p["id"]]["out"] = o
        # funding: chia cho vi the dang mo luc tra, theo khoi luong
        fund = defaultdict(float)
        for t, usd in funding.get(sym, []):
            live = []
            for p in ps:
                mi = m.get(p["id"], {})
                t_in = mi["in"]["t"] if "in" in mi else p["entry_ts"]
                t_out = mi["out"]["t"] if "out" in mi else (p["exit_ts"] or 10 ** 15)
                if t_in < t <= t_out:
                    live.append(p)
            q = sum(p["qty"] for p in live)
            for p in live:
                fund[p["id"]] += usd * p["qty"] / q
        for p in ps:
            mi = m.get(p["id"], {})
            if p["open"] or "in" not in mi or "out" not in mi:
                continue
            i, o = mi["in"], mi["out"]
            fee = i["fee"] * p["qty"] / i["qty"] + o["fee"] * p["qty"] / o["qty"]
            gross = p["side"] * p["qty"] * (o["px"] - i["px"])
            net = gross - fee + fund[p["id"]]
            notional = float(p.get("notional") or 0) or p["qty"] * i["px"]
            out.append({"id": p["id"], "symbol": sym, "entry_px": i["px"], "exit_px": o["px"],
                        "exit_ts": o["t"], "fee_usd": fee, "fund_usd": fund[p["id"]],
                        "gross_usd": gross, "pnl_usd": net, "pnl_bps": net / notional * 1e4,
                        "old_usd": notional * float(p["pnl_bps"]) / 1e4
                        if p.get("pnl_bps") is not None else None})
    return out


def _fetch(t: Trader, syms: list, t0: int) -> tuple[dict, dict]:
    now = int(time.time() * 1000)
    fills = {}
    for s in syms:
        rows, a = [], t0
        while a < now:                       # userTrades: toi da 7 ngay moi lan goi
            b = min(a + 7 * DAY - 1, now)
            while True:
                r = t._call("GET", "/fapi/v1/userTrades", symbol=s, startTime=a, endTime=b, limit=1000)
                rows += r
                if len(r) < 1000:
                    break
                a = int(r[-1]["time"]) + 1
            a = b + 1
        fills[s] = rows
    funding = defaultdict(list)
    a = t0
    while a < now:
        b = min(a + 7 * DAY - 1, now)
        while True:
            r = t._call("GET", "/fapi/v1/income", incomeType="FUNDING_FEE",
                        startTime=a, endTime=b, limit=1000)
            for x in r:
                funding[x["symbol"]].append((int(x["time"]), float(x["income"])))
            if len(r) < 1000:
                break
            a = int(r[-1]["time"]) + 1
        a = b + 1
    return fills, funding


def recompute(write: bool = True) -> dict:
    """Tinh lai toan bo vi the that da dong. Chi doc san; ghi so khi `write`."""
    cx = db.connect()
    try:
        pos = [dict(r) for r in cx.execute("SELECT * FROM positions WHERE mode='live'")]
    finally:
        cx.close()
    if not pos:
        return {"n": 0, "rows": []}
    t0 = min(p["entry_ts"] for p in pos) - DAY
    if t0 < time.time() * 1000 - 180 * DAY:
        # san chi giu userTrades / income ~6 thang / 3 thang
        db.log("warn", "tính lại lãi đã chốt: có vị thế cũ hơn lịch sử sàn còn giữ — các vị thế đó giữ số cũ")
    t = Trader()
    try:
        fills, funding = _fetch(t, sorted({p["symbol"] for p in pos}), int(t0))
    finally:
        t.close()
    rows = attribute(pos, fills, funding)
    closed = [p for p in pos if not p["open"]]
    miss = sorted({p["id"] for p in closed} - {r["id"] for r in rows})
    if write and rows:
        with db.tx() as cx:
            for r in rows:
                cx.execute("UPDATE positions SET entry_px=?, exit_px=?, exit_ts=?, pnl_bps=?,"
                           " fee_usd=?, fund_usd=? WHERE id=?",
                           (r["entry_px"], r["exit_px"], r["exit_ts"], r["pnl_bps"],
                            r["fee_usd"], r["fund_usd"], r["id"]))
    old = sum(r["old_usd"] or 0 for r in rows)
    new = sum(r["pnl_usd"] for r in rows)
    res = {"ts": int(time.time() * 1000), "n": len(rows), "closed": len(closed), "missing": miss,
           "old_usd": old, "new_usd": new, "fee_usd": sum(r["fee_usd"] for r in rows),
           "fund_usd": sum(r["fund_usd"] for r in rows), "rows": rows}
    if write:
        db.kv_set("repnl_last", {k: v for k, v in res.items() if k != "rows"})
        db.log("warn" if abs(new - old) > 0.01 else "info",
               f"tính lại lãi đã chốt từ sàn: {len(rows)}/{len(closed)} vị thế · "
               f"{old:+.2f} → {new:+.2f} USD (phí thật {res['fee_usd']:.2f}, funding {res['fund_usd']:+.2f})"
               + (f" · {len(miss)} vị thế không ghép được lệnh trên sàn: #{', #'.join(map(str, miss))}"
                  if miss else ""))
    return res
