"""Chot loi lenh BAN dong luong (PP1) giua cac luot ngay — luat C4 = F08 + P16.

Nghien cuu 05/11/2026 (docs/pp1-tp-c4.md, scratch tbc1_merge): bot 6 PP khong
tran, lai +491 USD, Sharpe 2,335 → 2,455, tong lo cac thang am −2.064 → −1.712
(KTC Šidák [+91; +745]), duong o 6/6 nam va 6/6 moc cat ngay, vuot chot ngau
nhien (p 0,000). So thang am KHONG doi (17/67) — luat lam thang am nong hon.

Chi lenh BAN cua PP1 (strategy 'xsmom', side −1). Kiem o gia dong cua nen 1H vua
chot (lich chay phut 1 moi gio), lai u = side × (gia/gia vao − 1) / (r_usd/notional):
  F08: u ≥ F08_M (0,5R) VA ti trong khoi luong spot q ≤ 1 − F08_X (0,8).
       s = KL spot / (KL spot + KL perp) cong 3 ngay UTC gan nhat da dong
       (spot: quote volume nen 1D cap spot cung ten hoac bo tien to 1000/1M;
       perp: close × volume nen 1D); q = s ÷ trung vi s cua 60 ngay (≥ 30 ngay
       co so lieu). Ma khong co cap spot: luat khong chay.
  P16: trong ngay giu thu P16_H (4) — ngay UTC chua gio vao + 3 — u ≥ P16_M (1R).
Thoa mot trong hai → dong toan bo lenh o gia thi truong (≈ open nen 1H ke tiep),
qua executor nhu luot ngay (giay: gia hien tai; that: limit/market reduceOnly).
Cho trong de nguyen toi lan tai can bang cua so do. Nen 00:00 UTC: bo qua so tai
can bang o luot 00:05 (luot ngay quyet dinh) — giong engine nghien cuu.
Lai/lo da chot cong vao `tp_realised:<mode>`; luot ngay ke tiep cong vao von.
Bat/tat: XSMOM_TP (tab «Cấu hình» khoa `xsmom_tp`).
"""
from __future__ import annotations

import time

import httpx
import numpy as np

from . import db, executor, data, runner, settings, strategies as ST
from .binance import DAY, PublicApi
from .config import CFG, FEE_BPS

HR = 3_600_000
SPOT_REST = "https://api.binance.com"
NAME = "pp1tp"


def _base(sym: str) -> str:
    b = sym[:-4]
    for pre in ("1000000", "1000", "1M"):
        if b.startswith(pre) and len(b) > len(pre):
            return b[len(pre):]
    return b


def _u(p: dict, px: float) -> float:
    n, r = float(p.get("notional") or 0), float(p.get("r_usd") or 0)
    if not (n > 0 and r > 0 and px > 0):
        return float("nan")
    return int(p["side"]) * (px / float(p["entry_px"]) - 1) / (r / n)


def _spot_daily(cl: httpx.Client, sym: str, start: int) -> tuple[str, dict]:
    """(ma spot dung duoc, {ngay: quote volume}) — thu cung ten roi bo tien to."""
    smap = db.kv_get("pp1tp_spotmap", {}) or {}
    cands = [smap[sym]] if smap.get(sym) else ([] if sym in smap else list(dict.fromkeys([sym, _base(sym) + "USDT"])))
    for c in cands:
        r = cl.get("/api/v3/klines", params={"symbol": c, "interval": "1d", "startTime": start, "limit": 100})
        if r.status_code != 200:
            continue
        rows = r.json()
        if isinstance(rows, list) and rows:
            smap[sym] = c
            db.kv_set("pp1tp_spotmap", smap)
            return c, {int(x[0]): float(x[7]) for x in rows}
    if sym not in smap:
        smap[sym] = ""
        db.kv_set("pp1tp_spotmap", smap)
    return "", {}


def spot_q(api: PublicApi, syms: list, d: int) -> dict:
    """{ma: q} cho ngay UTC d (ms, da dong). Cache theo ngay trong kv `pp1tp_q`."""
    c = db.kv_get("pp1tp_q") or {}
    if c.get("day") != d:
        c = {"day": d, "q": {}}
    need = [s for s in syms if s not in c["q"]]
    if need:
        start = d - 70 * DAY
        days = np.arange(start, d + DAY, DAY, dtype=np.int64)
        with httpx.Client(base_url=SPOT_REST, timeout=20.0, headers={"User-Agent": "crypto-live/1"}) as cl:
            for s in need:
                q = None
                try:
                    sp, sv = _spot_daily(cl, s, int(start))
                    if sp:
                        pk = {int(x[0]): float(x[4]) * float(x[5]) for x in api.klines(s, int(start), 100)}
                        SQ = np.array([sv.get(int(t), np.nan) for t in days])
                        PQ = np.array([pk.get(int(t), np.nan) for t in days])
                        with np.errstate(all="ignore"):
                            sq3 = SQ[2:] + SQ[1:-1] + SQ[:-2]
                            pq3 = PQ[2:] + PQ[1:-1] + PQ[:-2]
                            S3 = sq3 / (sq3 + pq3)
                        S3[~(S3 > 0)] = np.nan
                        w = S3[-60:]
                        if np.isfinite(S3[-1]) and np.isfinite(w).sum() >= 30:
                            q = float(S3[-1] / np.nanmedian(w))
                except Exception as e:
                    db.log("warn", f"PP1 chốt lời: tỉ trọng spot {s} lỗi: {e}")
                    continue
                c["q"][s] = q
        db.kv_set("pp1tp_q", c)
    return {s: c["q"].get(s) for s in syms}


def _close_1h(api: PublicApi, sym: str, close_ms: int) -> float | None:
    """Gia dong cua nen 1H [close_ms − 1h, close_ms)."""
    k = api.klines_1h(sym, close_ms - HR, 2)
    for x in k:
        if int(x[0]) == close_ms - HR and int(x[6]) < int(time.time() * 1000):
            return float(x[4])
    return None


def run_once() -> dict:
    st = {"t": int(time.time() * 1000), "checked": 0, "closed": [], "errors": [], "skipped": []}
    if not settings.pp1x().get("tp"):
        db.kv_set("pp1tp_last", {**st, "off": True})
        return st
    m = runner.mode()
    book = [p for p in runner.open_positions(m) if p["strategy"] == "xsmom" and int(p["side"]) < 0]
    st["mode"] = m
    if not book:
        db.kv_set("pp1tp_last", st)
        return st
    if not runner.RUN_LOCK.acquire(timeout=600):
        db.log("warn", "PP1 chốt lời: lượt ngày giữ khoá quá 10 phút — bỏ lượt giờ này")
        return st
    api = PublicApi()
    try:
        now = int(time.time() * 1000)
        close_ms = now // HR * HR
        book = [p for p in runner.open_positions(m) if p["strategy"] == "xsmom" and int(p["side"]) < 0]
        skip_sl = None
        if close_ms % DAY == 0:              # nen ngay vua dong: so den luot do luot 00:05 quyet dinh
            e = db.kv_get("xsmom_epoch")
            if e is not None:
                skip_sl = ST.xsmom_sleeve_of(close_ms - DAY, int(e))
        d_q = close_ms // DAY * DAY - DAY    # ngay UTC gan nhat da dong truoc gio quyet dinh
        x08, m08 = float(CFG.xsmom_tp_f08_x), float(CFG.xsmom_tp_f08_m)
        h16, m16 = int(CFG.xsmom_tp_p16_h), float(CFG.xsmom_tp_p16_m)
        try:
            Q = spot_q(api, sorted({p["symbol"] for p in book}), int(d_q))
        except Exception as e:
            Q = {}
            st["errors"].append(f"tỉ trọng spot: {e}")
        px1: dict = {}
        acts = []
        for p in book:
            if skip_sl is not None and p.get("sleeve") == skip_sl:
                st["skipped"].append(f"{p['symbol']} sổ {p['sleeve']}: tái cân bằng lượt 00:05")
                continue
            s = p["symbol"]
            if s not in px1:
                try:
                    px1[s] = _close_1h(api, s, close_ms)
                except Exception as e:
                    px1[s] = None
                    st["errors"].append(f"{s}: nến 1H lỗi {e}")
            c = px1[s]
            if not c:
                continue
            st["checked"] += 1
            u = _u(p, c)
            if not np.isfinite(u):
                continue
            why = None
            q = Q.get(s)
            if q is not None and q <= 1 - x08 and u >= m08:
                why = f"chốt lời F08 · lãi {u:.2f}R · tỉ trọng spot {q:.2f}× TB"
            E = int(p["entry_ts"]) // DAY * DAY
            if why is None and E + (h16 - 1) * DAY < close_ms <= E + h16 * DAY and u >= m16:
                why = f"chốt lời P16 · ngày giữ {h16} · lãi {u:.2f}R"
            if why:
                acts.append({"action": "CLOSE", **p, "exit_why": why})
        if acts:
            prices = api.prices()
            eq = runner.equity_now()
            filt = data.filters(api) if m == "live" else {}
            done = executor.execute(None, acts, eq, prices, filt, m)
            realised = 0.0
            msgs = []
            with db.tx() as cx:
                for a in done:
                    if a.get("status") in ("lỗi", "bỏ qua", "không khớp"):
                        st["errors"].append(f"{a['symbol']}: {a.get('status')}")
                        continue
                    bps = (a["px"] - a["entry_px"]) / a["entry_px"] * 1e4 * a["side"] - FEE_BPS
                    usd = float(a.get("notional") or 0) * bps / 1e4
                    realised += usd
                    cx.execute("UPDATE positions SET open=0, exit_px=?, exit_ts=?, exit_why=?, pnl_bps=? WHERE id=?",
                               (a["px"], int(time.time() * 1000), a["exit_why"], bps, a["id"]))
                    st["closed"].append({"symbol": a["symbol"], "sleeve": a.get("sleeve"), "px": a["px"],
                                         "bps": round(bps, 1), "usd": round(usd, 2), "why": a["exit_why"]})
                    msgs.append(f"PP1 {a['exit_why']} · {a['symbol']} (sổ {a.get('sleeve')}) "
                                f"{a['px']:g} · {bps:+.0f} bps · {usd:+.2f} USD")
            for x in msgs:                      # ghi log SAU khi dong giao dich (log mo ket noi rieng)
                db.log("info", x)
            if realised:
                key = f"tp_realised:{m}"
                db.kv_set(key, float(db.kv_get(key, 0) or 0) + realised)
            st["realised"] = realised
            if m == "live" and st["closed"]:
                runner.safety_now(filt)
        st["q"] = {k: (round(v, 3) if v is not None else None) for k, v in Q.items()}
    finally:
        api.close()
        runner.RUN_LOCK.release()
        db.kv_set("pp1tp_last", st)
    return st
