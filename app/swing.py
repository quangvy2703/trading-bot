"""Hai chien luoc khung ngay tu dot YouTube 2 — TSVW va DSRM (docs/tsvw-dsrm.md).

  TSVW  "Number One VWAP Day Trading Strategy" (The Secret Mindset): day V (day
        moi 50 nen) → close vuot co (dinh 10 nen truoc day) trong 10 nen → hoi
        ve co, VWAP neo tai day nam trong 0,5 ATR quanh co → nen xanh dong lai
        tren co. Stop = AVWAP − 0,25 ATR; chot 2R. Ban la doi xung (dinh V).
  DSRM  "Stochastic + RSI + MACD (Proven 100x)" (Data Trader): Stoch(14,3,3) K
        va D < 20 trong 3 nen truoc (chua cham 80 tu do) → RSI(14) > 50 va MACD
        > duong tin hieu (canh len). Stop = day 10 nen; chot 1,5R. Ban doi xung.
  IMD   "Impulse MACD" (TradingLab, LazyBear) CHI BAN (docs/impulse-macd-ban.md):
        duong tin hieu SMA9 cat LEN tren Impulse MACD khi ca hai (nen truoc) > m ×
        TB 200 nen |md| (m 2) → ban. Stop = dinh 5 nen; chot 10R. Nghien cuu:
        scripts/yt_imd.py, yt_imd_short_grid.py (o m2/10R/dinh 5).
Ca ba: tin hieu o nen 1D DA DONG, vao luc luot chay 00:05 UTC (= open nen ke
tiep), top 50 thanh khoan, mot lenh mot ma moi chien luoc, giu toi da 200 ngay.
Nghien cuu: scripts/yt_strats2.py, yt_deep2.py (kiem do ben 6/6), yt_deep2_R.py.

Chi bao o day CHEP NGUYEN dinh nghia cua ban nghien cuu (scripts/yt_strats.py,
yt_ind.py) — KHONG dung app/indicators.py: ATR o day la RMA cua Wilder bat dau
tu nen 0, RSI la RMA tu nen 0 voi n nen dau = nan, EMA bat dau tu x[0]. Doi
bat ky cai nao la tin hieu lech khoi backtest (xem tests trong
scripts/swing_parity.py).

Thoat (kiem o luot chay hang ngay, tren MOI nen da dong tu ngay vao — de mot
luot bi lo van bat duoc): cham stop → dong; cham chot → dong; du 200 ngay →
dong. Stop that su nam TREN SAN (dung an toan, executor.safety_level). Do lech
so voi backtest (chot khop o gia mo hom sau thay vi dung muc): TSVW −0,006R,
DSRM −0,007R moi lenh (scripts/yt_deep2 · softexit).
"""
from __future__ import annotations

import numpy as np

from .config import DSRM as LOCK_DSRM, IMD as LOCK_IMD, TSVW as LOCK_TSVW

DAY = 86_400_000
WARM = 210                      # nen khoi dong chi bao (nhu nghien cuu)
MINRISK = 0.001                 # bo tin hieu co stop < 0,1% gia


# ---------------------------------------------------------------- chi bao (ban nghien cuu)
def ema(x, n):
    a = 2.0 / (n + 1)
    out = np.empty(len(x))
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


def rma(x, n):
    out = np.empty(len(x))
    out[0] = x[0]
    a = 1.0 / n
    for i in range(1, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


def sma(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        cs = np.concatenate(([0.0], np.cumsum(x)))
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def nz_sma(x, n):
    out = np.full(len(x), np.nan)
    f = np.flatnonzero(np.isfinite(x))
    if len(f):
        out[f[0]:] = sma(np.nan_to_num(x[f[0]:]), n)
    return out


def rollmin(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = np.lib.stride_tricks.sliding_window_view(x, n).min(1)
    return out


def rollmax(x, n):
    return -rollmin(-x, n)


def atr(h, l, c, n=14):
    pc = np.concatenate(([c[0]], c[:-1]))
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return rma(tr, n)


def rsi(c, n):
    d = np.diff(c, prepend=c[0])
    up = rma(np.maximum(d, 0), n)
    dn = rma(np.maximum(-d, 0), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + up / dn)
    r = np.where(dn == 0, 100.0, r)
    r[:n] = np.nan
    return r


def stoch(h, l, c, k, d=3, smooth=3):
    lo, hi = rollmin(l, k), rollmax(h, k)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = 100 * (c - lo) / (hi - lo)
    K = nz_sma(raw, smooth)
    return K, nz_sma(K, d)


def zlema(x, n):
    e1 = ema(x, n)
    return e1 + (e1 - ema(e1, n))


def shift(x, k=1):
    out = np.full(len(x), np.nan)
    out[k:] = x[:-k]
    return out


def cross_up(a, b):
    out = np.zeros(len(a), bool)
    out[1:] = (a[1:] > b[1:]) & (a[:-1] <= b[:-1])
    return out


def bars_since(mask):
    n = len(mask)
    idx = np.where(mask, np.arange(n), -10 ** 9)
    return np.arange(n) - np.maximum.accumulate(idx)


def rising(mask):
    prev = np.zeros(len(mask), bool)
    prev[1:] = mask[:-1]
    return mask & ~prev


# ---------------------------------------------------------------- tin hieu
def tsvw_signals(b: dict, P: dict | None = None) -> list:
    """Moi tin hieu TSVW tren toan lich su: (chi so nen tin hieu q, chieu, stop).

    Chep sig_vbot2 (scripts/yt_deep2.py) — kha nang duy nhat khac: cho phep
    nen tin hieu la nen DA DONG CUOI CUNG (nghien cuu can them nen q+1 de vao).
    """
    P = P or LOCK_TSVW
    N, K, B, W = int(P["N"]), int(P["K"]), int(P["B"]), int(P["W"])
    o, h, l, c, v = b["o"], b["h"], b["l"], b["c"], b["v"]
    at = atr(h, l, c, 14)
    n = len(c)
    out = []
    for side in (1, -1):
        t = N + 10
        while t < n - 1:
            new = True
            for q in range(t - N, t):
                if (side == 1 and l[q] <= l[t]) or (side == -1 and h[q] >= h[t]):
                    new = False
                    break
            if not new:
                t += 1
                continue
            Nk = max(h[t - K:t]) if side == 1 else min(l[t - K:t])
            tb = -1
            for q in range(t + 1, min(t + B + 1, n)):
                if (side == 1 and l[q] < l[t]) or (side == -1 and h[q] > h[t]):
                    break
                if (c[q] - Nk) * side > 0:
                    tb = q
                    break
            if tb < 0:
                t += 1
                continue
            pv = float(np.sum((h[t:tb + 1] + l[t:tb + 1] + c[t:tb + 1]) / 3 * v[t:tb + 1]))
            vv = float(np.sum(v[t:tb + 1]))
            done = False
            touched = False
            q = tb
            for q in range(tb + 1, min(tb + W + 1, n)):
                pv += (h[q] + l[q] + c[q]) / 3 * v[q]
                vv += v[q]
                aw = pv / vv if vv > 0 else c[q]
                if (side == 1 and l[q] <= Nk + 0.25 * at[q]) or (side == -1 and h[q] >= Nk - 0.25 * at[q]):
                    touched = True
                if touched and abs(aw - Nk) <= 0.5 * at[q] and (c[q] - Nk) * side > 0 and (c[q] - o[q]) * side > 0:
                    out.append((q, side, float(aw - 0.25 * at[q] * side)))
                    done = True
                    break
                if (side == 1 and c[q] < l[t]) or (side == -1 and c[q] > h[t]):
                    break
            t = q + 1 if done else t + 1
    return out


def dsrm_signals(b: dict, P: dict | None = None) -> list:
    """Moi tin hieu DSRM: (chi so nen tin hieu, chieu, stop)."""
    P = P or LOCK_DSRM
    Wn, lv, sw = int(P["W"]), float(P["lv"]), int(P["sw"])
    hi = 100 - lv
    h, l, c = b["h"], b["l"], b["c"]
    n = len(c)
    K, D = stoch(h, l, c, 14, 3, 3)
    m_ = ema(c, 12) - ema(c, 26)
    ms = ema(m_, 9)
    r = rsi(c, 14)
    with np.errstate(invalid="ignore"):
        aL = bars_since((K < lv) & (D < lv))
        aS = bars_since((K > hi) & (D > hi))
        cL = rising((r > 50) & (m_ > ms)) & (aL <= Wn) & (bars_since(K > hi) > aL)
        cS = rising((r < 50) & (m_ < ms)) & (aS <= Wn) & (bars_since(K < lv) > aS)
    cL[:WARM] = False
    cS[:WARM] = False
    sL, sH = rollmin(l, sw), rollmax(h, sw)
    return ([(int(j), 1, float(sL[j])) for j in np.flatnonzero(cL)]
            + [(int(j), -1, float(sH[j])) for j in np.flatnonzero(cS)])


IMD_WARM = 250                  # nghien cuu bo 250 nen dau (SMA 200 cua |md| + do tre)


def imd(b: dict):
    """Impulse MACD (LazyBear) — chep scripts/yt_imd.py imd(): md, duong tin hieu, muc 'cao'."""
    h, l, c = b["h"], b["l"], b["c"]
    hlc3 = (h + l + c) / 3
    hi, lo, mi = rma(h, 34), rma(l, 34), zlema(hlc3, 34)
    md = np.where(mi > hi, mi - hi, np.where(mi < lo, mi - lo, 0.0))
    return md, sma(md, 9), shift(sma(np.abs(md), 200), 1)


def imd_signals(b: dict, P: dict | None = None) -> list:
    """Moi tin hieu IMD chi ban: (chi so nen tin hieu, -1, stop = dinh `sw` nen)."""
    P = P or LOCK_IMD
    m, sw = float(P["m"]), int(P["sw"])
    md, sb, lev = imd(b)
    with np.errstate(invalid="ignore"):
        S = cross_up(sb, md) & (shift(md, 1) > m * lev) & (shift(sb, 1) > m * lev)
    S[:IMD_WARM] = False
    sH = rollmax(b["h"], sw)
    return [(int(j), -1, float(sH[j])) for j in np.flatnonzero(S)]


SIGNALS = {"tsvw": tsvw_signals, "dsrm": dsrm_signals, "imd": imd_signals}
PARAMS = {"tsvw": LOCK_TSVW, "dsrm": LOCK_DSRM, "imd": LOCK_IMD}
NAME = {"tsvw": "TSVW (đáy V + AVWAP)", "dsrm": "DSRM (Stoch+RSI+MACD)", "imd": "Impulse MACD bán"}


def signals_today(strategy: str, P: dict, rank: dict, day: int, held: set,
                  nobuy: dict | None = None) -> list:
    """Tin hieu cua chien luoc tren nen DA DONG `day`, cho cac ma top N chua giu.

    Stop la muc tuyet doi tinh tren nen tin hieu; co lenh va muc chot tinh tu
    gia khop (runner/_book_open). Ma co thong bao huy niem yet: bo chieu MUA.
    """
    prm = PARAMS[strategy]
    fn = SIGNALS[strategy]
    out = []
    for sym, d in P.items():
        if sym in held or rank.get(sym, 10 ** 9) > prm["topn"]:
            continue
        j = int(np.searchsorted(d["t"], day))
        if j >= len(d["t"]) or d["t"][j] != day or j < WARM:
            continue
        b = {k: d[k][:j + 1] for k in ("t", "o", "h", "l", "c", "v")}
        for q, side, stop in fn(b, prm):
            if q != j:
                continue
            if side > 0 and nobuy and sym in nobuy:
                continue
            px = float(b["c"][j])
            rf = (px - stop) / px * side if px > 0 else 0.0
            if not (np.isfinite(rf) and rf >= MINRISK):
                continue
            out.append({"symbol": sym, "side": side, "stop": stop, "rf": rf,
                        "close": px, "rank": rank.get(sym)})
    out.sort(key=lambda x: (x["rank"] or 10 ** 9))
    return out


def exits(P: dict, day: int, positions: list) -> list:
    """Vi the can dong hom nay: tren moi nen da dong tu ngay vao toi `day`,
    cham stop (uu tien) hoac cham chot; hoac da giu du `hold` ngay."""
    out = []
    for p in positions:
        d = P.get(p["symbol"])
        if d is None:
            out.append((p, "hết dữ liệu"))
            continue
        j = int(np.searchsorted(d["t"], day))
        if j >= len(d["t"]) or d["t"][j] != day:
            out.append((p, "hết dữ liệu"))
            continue
        a = int(np.searchsorted(d["t"], int(p["entry_ts"]) // DAY * DAY))
        seg = slice(a, j + 1)
        side, stop, tp = p["side"], p.get("stop"), p.get("tp")
        if a > j:
            continue
        lo, hi = float(np.min(d["l"][seg])), float(np.max(d["h"][seg]))
        if stop and ((side > 0 and lo <= stop) or (side < 0 and hi >= stop)):
            out.append((p, "cắt lỗ"))
        elif tp and ((side > 0 and hi >= tp) or (side < 0 and lo <= tp)):
            out.append((p, "chốt lời"))
        elif (day - int(p["entry_ts"]) // DAY * DAY) // DAY + 1 >= PARAMS[p["strategy"]]["hold"]:
            out.append((p, f"hết {PARAMS[p['strategy']]['hold']} ngày"))
    return out
