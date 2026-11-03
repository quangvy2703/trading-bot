"""So giay VSA 4H — "day qua vung cung" roi nen giam khoi luong thap.

Tom Williams, *Master the Markets* (VSA). Nghien cuu: scripts/gh_vsa.py,
gh_vsa_verify.py, gh_vsa_corr.py; dac ta: docs/vsa-push-4h.md. Day la o duy
nhat trong 324 o VSA song qua kiem do ben, nhung duoc chon SAU khi nhin luoi
— nen chi ghi so giay de doi chieu voi backtest, KHONG BAO GIO dat lenh that.

Moi 4 gio (00:02, 04:02, … UTC, ngay sau khi nen 4H dong), voi moi ma top N
thanh khoan (hang ngay da dong, nhu bot chinh):
  tin hieu o nen vua dong i (dinh nghia y het gh_vsa.feats, ho L7 PUSH + nen bg):
    * trong 10 nen truoc co nen "day qua vung cung": nen tang, bien do > 1,5×
      TB 30 nen, KL > 1,5× TB 30 nen, dong o 1/3 tren, close vuot dinh 20 nen;
    * trong 20 nen truoc co dau hieu manh: nen giam KL cao dong >= giua,
      hoac nen rong cham day 20 nen KL cao dong >= 0,6;
    * nen i giam (close < close truoc) va KL nho hon CA HAI nen truoc.
  → mua GIA o open nen i+1, ra o close nen i+3 (giu 3 nen = 12 gio). Mot lenh
  mot ma mot luc. Phi 10 bps khu hoi + funding thuc (long tra).
Luot chay tre hon 15 phut sau open nen vao thi ghi "bỏ lỡ", khong vao — gia
open da qua, vao luc do khong con la phep thu cua backtest.
"""
from __future__ import annotations

import json
import time

import numpy as np

from . import db, runner
from .binance import PublicApi
from .config import CFG, FEE_BPS

H4 = 4 * 3_600_000
DAY = 86_400_000
HOLD = 3
LATE_MS = 15 * 60_000
NBARS = 150


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
    now = int(time.time() * 1000)
    st = {"t": now, "scanned": 0, "signals": 0, "opened": 0, "missed": 0, "closed": 0, "errors": []}
    api = PublicApi()
    try:
        syms = _top(CFG.vsa_topn)
        held = {r["symbol"]: r for r in _open_rows()}
        for sym in sorted(set(syms) | set(held)):
            try:
                k = _klines(api, sym)
            except Exception as e:
                st["errors"].append(f"{sym}: {e}")
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
        api.close()
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
            "usd_per_trade": CFG.vsa_paper_usd, "topn": CFG.vsa_topn,
            "backtest": {"n": 3594, "mean": 38.7, "median": -6.9, "win": 0.49, "per_day": 1.8}}
