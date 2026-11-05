"""Windfall PP1 — dong lenh dong luong khi mot nen 15m chay co loi bat thuong, mo lai o luot ngay ke tiep.

Y tuong nguoi dung 06/11/2026 (nghien cuu scratch qs11/pp1, o «PP1-both 15m k25 re»): bot 6 PP khong tran, chua co
C4, lai +773 USD, Sharpe +0,108 (KTC Šidák-60 [+0,004; +0,287]), duong 6/6 nam, ca nua dev lan holdout; NHUNG
walk-forward truot, 10 ngay tot nhat ≈ toan bo phan lai (chu yeu cac ngay sap chop nhoang), so thang am khong doi.
Kiem cung C4: scratch qs14.

Luat (ca hai chan PP1, strategy 'xsmom'), moi nen 15m vua dong (lich phut 1/16/31/46):
  z = ln(C_t / C_{t−1}) / sd(W = 288 log-return 15m truoc do, khong gom t; ddof 1; ≥ 90% co so lieu)
  side × z ≥ K (25) → dong toan bo lenh o gia thi truong (≈ open nen 15m ke tiep), qua executor nhu luot ngay.
Stop 3R tren san cham truoc thi lenh da dong, khong con trong so. Nen dong luc 00:00 UTC: bo qua so tai can bang o
luot 00:05 (luot ngay quyet dinh).
Mo lai (XSMOM_WF_RE = 1): luot ngay dau tien SAU gio dong (00:05 UTC), neu so cua lenh khong den luot tai can bang
hom do thi mo lai cung so / ma / chieu, co lenh tinh lai 1R/(σ30·√7) o gia moi (runner.build_target). So den luot
thi lan tai can bang quyet dinh. Khong kiem lai loc MA / BSADF (so van giu ma do), giong engine nghien cuu.
Lai/lo da chot cong vao `tp_realised:<mode>` (chung voi C4); luot ngay ke tiep cong vao von.
Bat/tat: XSMOM_WF (tab «Cấu hình» khoa `xsmom_wf`).
"""
from __future__ import annotations

import math
import time

import numpy as np

from . import db, executor, data, runner, settings, strategies as ST
from .binance import DAY, PublicApi
from .config import CFG, FEE_BPS

TF_MS = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000}
KEY_RE = "pp1wf_reenter"


def _z(api: PublicApi, sym: str, close_ms: int, tf: str, w: int) -> float | None:
    """z cua nen [close_ms − tf, close_ms) so voi sd W nen truoc do. None khi thieu so lieu."""
    step = TF_MS[tf]
    t0 = close_ms - (w + 2) * step
    k = api.klines_iv(sym, tf, t0, w + 2)
    now = int(time.time() * 1000)
    cl = {int(x[0]): float(x[4]) for x in k if int(x[6]) < now}
    grid = t0 + step * np.arange(w + 2, dtype=np.int64)
    if int(grid[-1]) not in cl:
        return None
    c = np.array([cl.get(int(t), np.nan) for t in grid])
    with np.errstate(all="ignore"):
        r = np.diff(np.log(c))
    rt, prev = r[-1], r[:-1]
    ok = np.isfinite(prev)
    if not np.isfinite(rt) or ok.sum() < 0.9 * w:
        return None
    sd = float(np.std(prev[ok], ddof=1))
    return float(rt / sd) if sd > 0 else None


def pending(before_ms: int) -> list:
    """Lenh windfall da dong truoc moc `before_ms` (00:00 UTC cua luot ngay) — cho runner mo lai."""
    return [x for x in (db.kv_get(KEY_RE, []) or []) if int(x["exit_ts"]) < before_ms]


def consume(before_ms: int) -> None:
    """Bo cac muc da den luot (da mo lai, hoac so den luot tai can bang nen bo)."""
    db.kv_set(KEY_RE, [x for x in (db.kv_get(KEY_RE, []) or []) if int(x["exit_ts"]) >= before_ms])


def reentry_targets(P: dict, day: int, sl: int, r_xsmom: float, have: set, nobuy: dict | None) -> list:
    """Muc tieu mo lai cho runner.build_target. `day` = nen ngay vua dong; quyet dinh luc day + 1 ngay."""
    _, X = settings.strat()
    out = []
    for it in pending(day + DAY):
        s, side, sv = it["symbol"], int(it["side"]), int(it["sleeve"])
        if sv == sl or sv >= X["sleeves"] or (sv, s, side) in have:
            continue
        if side > 0 and nobuy and s in nobuy:
            continue
        d = P.get(s)
        j = ST._idx(d, day) if d else None
        L = X["lookback"]
        if j is None or j - L < 0:
            continue
        c = d["c"]
        with np.errstate(all="ignore"):
            vol = float(np.nanstd(np.log(c[j - L + 1:j + 1] / c[j - L:j])))
        rf = vol * math.sqrt(X["hold"])
        if not (rf > 0):
            continue
        have.add((sv, s, side))
        out.append({"strategy": "xsmom", "sleeve": sv, "symbol": s, "side": side,
                    "stop": None, "r_usd": r_xsmom, "notional": r_xsmom / rf,
                    "why": f"mở lại sau windfall · R {rf*100:.1f}%"})
    return out


def run_once() -> dict:
    st = {"t": int(time.time() * 1000), "checked": 0, "closed": [], "errors": [], "skipped": []}
    if not settings.pp1x().get("wf"):
        db.kv_set("pp1wf_last", {**st, "off": True})
        return st
    side_ok = {"both": (1, -1), "long": (1,), "short": (-1,)}.get(CFG.xsmom_wf_side, (1, -1))
    m = runner.mode()
    st["mode"] = m
    if not [p for p in runner.open_positions(m) if p["strategy"] == "xsmom"]:
        db.kv_set("pp1wf_last", st)
        return st
    if not runner.RUN_LOCK.acquire(timeout=600):
        db.log("warn", "PP1 windfall: lượt ngày giữ khoá quá 10 phút — bỏ lượt này")
        return st
    api = PublicApi()
    try:
        tf, w, kk = CFG.xsmom_wf_tf, int(CFG.xsmom_wf_w), float(CFG.xsmom_wf_k)
        step = TF_MS[tf]
        now = int(time.time() * 1000)
        close_ms = now // step * step
        book = [p for p in runner.open_positions(m)
                if p["strategy"] == "xsmom" and int(p["side"]) in side_ok and int(p["entry_ts"]) < close_ms]
        skip_sl = None
        if close_ms % DAY == 0:              # nen ngay vua dong: so den luot do luot 00:05 quyet dinh
            e = db.kv_get("xsmom_epoch")
            if e is not None:
                skip_sl = ST.xsmom_sleeve_of(close_ms - DAY, int(e))
        Z: dict = {}
        acts = []
        for p in book:
            if skip_sl is not None and p.get("sleeve") == skip_sl:
                st["skipped"].append(f"{p['symbol']} sổ {p['sleeve']}: tái cân bằng lượt 00:05")
                continue
            s = p["symbol"]
            if s not in Z:
                try:
                    Z[s] = _z(api, s, close_ms, tf, w)
                except Exception as e:
                    Z[s] = None
                    st["errors"].append(f"{s}: nến {tf} lỗi {e}")
            z = Z[s]
            if z is None:
                continue
            st["checked"] += 1
            if int(p["side"]) * z >= kk:
                acts.append({"action": "CLOSE", **p,
                             "exit_why": f"windfall · nến {tf} z {z:+.1f} (ngưỡng {kk:g})"})
        if acts:
            prices = api.prices()
            eq = runner.equity_now()
            filt = data.filters(api) if m == "live" else {}
            done = executor.execute(None, acts, eq, prices, filt, m)
            realised = 0.0
            msgs, re_add = [], []
            with db.tx() as cx:
                for a in done:
                    if a.get("status") in ("lỗi", "bỏ qua", "không khớp"):
                        st["errors"].append(f"{a['symbol']}: {a.get('status')}")
                        continue
                    t_x = int(time.time() * 1000)
                    bps = (a["px"] - a["entry_px"]) / a["entry_px"] * 1e4 * a["side"] - FEE_BPS
                    usd = float(a.get("notional") or 0) * bps / 1e4
                    realised += usd
                    cx.execute("UPDATE positions SET open=0, exit_px=?, exit_ts=?, exit_why=?, pnl_bps=? WHERE id=?",
                               (a["px"], t_x, a["exit_why"], bps, a["id"]))
                    st["closed"].append({"symbol": a["symbol"], "sleeve": a.get("sleeve"), "side": a["side"],
                                         "px": a["px"], "bps": round(bps, 1), "usd": round(usd, 2),
                                         "why": a["exit_why"]})
                    msgs.append(f"PP1 {a['exit_why']} · {a['symbol']} (sổ {a.get('sleeve')}) "
                                f"{a['px']:g} · {bps:+.0f} bps · {usd:+.2f} USD")
                    if CFG.xsmom_wf_re and a.get("sleeve") is not None:
                        re_add.append({"sleeve": int(a["sleeve"]), "symbol": a["symbol"],
                                       "side": int(a["side"]), "exit_ts": t_x})
            for x in msgs:                      # ghi log SAU khi dong giao dich (log mo ket noi rieng)
                db.log("info", x)
            if re_add:
                db.kv_set(KEY_RE, (db.kv_get(KEY_RE, []) or []) + re_add)
            if realised:
                key = f"tp_realised:{m}"
                db.kv_set(key, float(db.kv_get(key, 0) or 0) + realised)
            st["realised"] = realised
            if m == "live" and st["closed"]:
                runner.safety_now(filt)
        st["z"] = {s: round(z, 2) for s, z in Z.items() if z is not None}
    finally:
        api.close()
        runner.RUN_LOCK.release()
        db.kv_set("pp1wf_last", st)
    return st
