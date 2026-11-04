"""Hai luat phu cho dong luong cat ngang (PP1), moi luat mot cong tac rieng.

Nghien cuu 04/11/2026 (docs/pp1-kase-funding.md). Ca hai chi DOC nen 1D va
funding trong kho, khong goi san.

  1. KASE (cong tac xsmom_kase): dong chan MUA khi gia dong cua thung muc
     Kase DevStop. Bien do 2 nen DTR = max(H, H[-1], C[-2]) − min(L, L[-1],
     C[-2]); muc = dinh cao nhat tu ngay vao − (TB DTR n nen + K × do lech
     chuan DTR n nen), chi duoc di len. Close < muc → dong o luot chay nay
     (khop open nen ke tiep, nhu tai can bang). Chan BAN khong doi. Ma vua
     dong khong mo lai trong cung luot; lan tai can bang sau cua so do mo lai
     neu ma van duoc chon — giong engine nghien cuu.
  2. FUNDING (cong tac xsmom_fund_veto): khong mo lenh BAN dong luong moi khi
     funding toan thi truong cuc thap (phe ban dong). Moi ngay: funding cong
     theo ngay UTC cua tung ma, TB 3 ngay; trung vi tren top 50 thanh khoan
     (trung vi gia tri giao dich 30 ngay); xep phan vi so voi toan bo lich su
     truoc do (>= 180 ngay). Phan vi <= nguong trong `hold` ngay gan nhat →
     chan. Lenh ban dang giu, chan mua va cac chien luoc khac khong doi.

  3. BSADF (cong tac xsmom_bsadf_veto, them 04/11/2026): khong mo lenh BAN
     dong luong cho ma co BSADF (Phillips–Shi–Yu, ADF 1 tre tren log close,
     sup tren cac cua so dai w0..W ket thuc o nen hom nay) > nguong 95% Monte
     Carlo (2000 buoc ngau nhien, seed 7: W 90 / w0 30 → 0,531). Thuc chat
     chan ban vao cu sap dang tang toc. Ma bi chan de trong, khong thay.

Tham so chot trong config (XSMOM_KASE_K/N, XSMOM_FUND_PCT/HOLD,
XSMOM_BSADF_W/W0/CV); bat/tat o tab «Cấu hình» hoac bien moi truong
XSMOM_KASE / XSMOM_FUND_VETO / XSMOM_BSADF.
"""
from __future__ import annotations

import numpy as np

from . import data, db
from .binance import DAY
from .config import CFG

AGG_WIN = 3          # so ngay lay TB funding
TOP_K = 50           # vu tru do funding
DV_WIN = 30          # cua so trung vi gia tri giao dich de xep hang
MIN_HIST = 180       # so ngay lich su toi thieu de xep phan vi


# ---------------------------------------------------------------- Kase
def _kase_levels(h: np.ndarray, l: np.ndarray, c: np.ndarray, a: int, n: int, k: float) -> np.ndarray:
    """Muc Kase (da ratchet) cho cac nen a..cuoi; NaN khi chua du du lieu."""
    m = len(c)
    pc2 = np.r_[np.nan, np.nan, c[:-2]]
    ph = np.r_[np.nan, h[:-1]]
    pl = np.r_[np.nan, l[:-1]]
    dtr = np.fmax(np.fmax(h, ph), pc2) - np.fmin(np.fmin(l, pl), pc2)
    out = np.full(m, np.nan)
    hh, lv = -np.inf, -np.inf
    for j in range(a, m):
        hh = max(hh, float(h[j]))
        if j - n + 1 >= 0:
            w = dtr[j - n + 1:j + 1]
            if np.all(np.isfinite(w)):
                lv = max(lv, hh - (float(w.mean()) + k * float(w.std())))
        if np.isfinite(lv):
            out[j] = lv
    return out


def kase_exits(P: dict, day: int, positions: list) -> dict:
    """{id(vi the): ly do} cho cac vi the MUA dong luong phai dong hom nay."""
    k, n = float(CFG.xsmom_kase_k), int(CFG.xsmom_kase_n)
    out = {}
    for p in positions:
        if p.get("strategy") != "xsmom" or int(p.get("side") or 0) != 1:
            continue
        d = P.get(p["symbol"])
        if d is None:
            continue
        t = d["t"]
        j = int(np.searchsorted(t, day))
        if j >= len(t) or t[j] != day:
            continue
        # nen vao = nen ngay chua thoi diem khop (khop luc 00:05 = open nen do)
        a = int(np.searchsorted(t, int(p["entry_ts"]) // DAY * DAY))
        if a >= len(t) or a > j:
            continue
        lv = _kase_levels(d["h"][:j + 1], d["l"][:j + 1], d["c"][:j + 1], a, n, k)[j]
        c = float(d["c"][j])
        if np.isfinite(lv) and c < lv:
            out[id(p)] = f"Kase: close {c:.6g} < mức {lv:.6g}"
    return out


# ---------------------------------------------------------------- funding
def _roll_median_rows(x: np.ndarray, w: int) -> np.ndarray:
    out = np.full_like(x, np.nan)
    for j in range(w - 1, x.shape[1]):
        out[:, j] = np.median(x[:, j - w + 1:j + 1], axis=1)
    return out


def funding_series() -> dict:
    """Chuoi trung vi funding top 50 (TB 3 ngay) va phan vi mo rong, theo ngay."""
    bars = {s: b for s, b in data.load_all(30).items() if data.is_crypto(b)}
    syms = sorted(bars)
    T = np.array(sorted({int(x) for b in bars.values() for x in b["t"]}), np.int64)
    n, m = len(syms), len(T)
    C = np.full((n, m), np.nan)
    V = np.full((n, m), np.nan)
    for i, s in enumerate(syms):
        b = bars[s]
        j = np.searchsorted(T, b["t"])
        C[i, j], V[i, j] = b["c"], b["v"]
    FD = np.zeros((n, m))
    ix = {s: i for i, s in enumerate(syms)}
    cx = db.connect()
    cx.row_factory = None
    try:
        rows = cx.execute("SELECT symbol, ts, rate FROM funding").fetchall()
    finally:
        cx.close()
    si = np.array([ix.get(r[0], -1) for r in rows])
    ts = np.array([r[1] for r in rows], np.int64)
    rt = np.array([r[2] for r in rows], float)
    ok = si >= 0
    dd = (ts[ok] // DAY) * DAY
    dj = np.searchsorted(T, dd)
    g = dj < m
    g[g] = T[dj[g]] == dd[g]
    np.add.at(FD, (si[ok][g], dj[g]), rt[ok][g])
    # top 50 theo trung vi gia tri giao dich 30 ngay (ngay khong co nen = 0)
    med = _roll_median_rows(np.nan_to_num(C * V, nan=0.0), DV_WIN)
    top = np.zeros((n, m), bool)
    for j in range(m):
        x = med[:, j]
        f = np.flatnonzero(x > 0)
        if len(f):
            top[f[np.argsort(-x[f])][:TOP_K], j] = True
    top &= np.isfinite(C)
    cs = np.cumsum(FD, 1)
    f3 = np.full_like(FD, np.nan)
    f3[:, AGG_WIN - 1:] = (cs[:, AGG_WIN - 1:]
                           - np.concatenate([np.zeros((n, 1)), cs[:, :-AGG_WIN]], 1)) / AGG_WIN
    agg = np.array([np.nanmedian(f3[top[:, j], j]) if top[:, j].any() else np.nan
                    for j in range(m)])
    pct = np.full(m, np.nan)
    hist = []
    for j in range(m):
        if not np.isfinite(agg[j]):
            continue
        hist.append(agg[j])
        if len(hist) >= MIN_HIST:
            h = np.asarray(hist)
            pct[j] = float((h <= agg[j]).mean())
    return {"T": T, "agg": agg, "pct": pct}


def fund_veto(day: int) -> dict:
    """Trang thai chan lenh BAN cho luot chay cua nen `day`. Cache theo ngay."""
    c = db.kv_get("pp1x_fund") or {}
    if c.get("day") == int(day) and c.get("pct_cut") == CFG.xsmom_fund_pct and c.get("hold") == CFG.xsmom_fund_hold:
        return c
    S = funding_series()
    T, pct, agg = S["T"], S["pct"], S["agg"]
    j = int(np.searchsorted(T, day))
    if j >= len(T) or T[j] != day:
        out = {"day": int(day), "active": False, "why": "chưa có nến hôm nay", "pct": None,
               "pct_cut": CFG.xsmom_fund_pct, "hold": CFG.xsmom_fund_hold}
    else:
        h = int(CFG.xsmom_fund_hold)
        win = np.nan_to_num(pct[max(0, j - h + 1):j + 1], nan=0.5)
        on = bool((win <= CFG.xsmom_fund_pct).any())
        out = {"day": int(day), "active": on,
               "pct": None if not np.isfinite(pct[j]) else float(pct[j]),
               "funding_med3": None if not np.isfinite(agg[j]) else float(agg[j]),
               "min_pct_window": float(win.min()) if len(win) else None,
               "pct_cut": CFG.xsmom_fund_pct, "hold": h}
    db.kv_set("pp1x_fund", out)
    return out


# ---------------------------------------------------------------- BSADF
def bsadf_at(y: np.ndarray, t: int, W: int, w0: int) -> float:
    """sup ADF t-stat cua b trong dy_k = a + b·y_{k-1} + c·dy_{k-1} tren cac cua so [s, t],
    do dai tu w0 den W. Giong het ban numba trong nghien cuu (qs2/t_f2_cands.py)."""
    s0 = t - w0 + 1
    if s0 < 2:
        return float("nan")
    sxx = np.zeros((3, 3)); sxy = np.zeros(3); syy = 0.0; n = 0
    for k in range(s0 + 2, t + 1):
        x = np.array([1.0, y[k - 1], y[k - 1] - y[k - 2]]); dy = y[k] - y[k - 1]
        if not (np.all(np.isfinite(x)) and np.isfinite(dy)):
            return float("nan")
        sxy += x * dy; sxx += np.outer(x, x); syy += dy * dy; n += 1
    best = -1e9
    s = s0
    while True:
        if n > 5 and abs(np.linalg.det(sxx)) > 1e-18:
            inv = np.linalg.inv(sxx)
            beta = inv @ sxy
            rss = syy - beta @ sxy
            if rss > 0:
                se = np.sqrt(rss / (n - 3) * inv[1, 1])
                if se > 0:
                    best = max(best, float(beta[1] / se))
        s -= 1
        if t - s + 1 > W or s < 0:
            break
        k = s + 2
        if k - 2 < 0:
            break
        x = np.array([1.0, y[k - 1], y[k - 1] - y[k - 2]]); dy = y[k] - y[k - 1]
        if not (np.all(np.isfinite(x)) and np.isfinite(dy)):
            break
        sxy += x * dy; sxx += np.outer(x, x); syy += dy * dy; n += 1
    return best


def bsadf_veto(P: dict, day: int, symbols: list) -> dict:
    """{ma: gia tri BSADF} cho cac ma phai chan lenh BAN hom nay."""
    W, w0, cv = int(CFG.xsmom_bsadf_w), int(CFG.xsmom_bsadf_w0), float(CFG.xsmom_bsadf_cv)
    out = {}
    for sym in symbols:
        d = P.get(sym)
        if d is None:
            continue
        j = int(np.searchsorted(d["t"], day))
        if j >= len(d["t"]) or d["t"][j] != day:
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            y = np.log(np.asarray(d["c"][:j + 1], float))
        b = bsadf_at(y, j, W, w0)
        if np.isfinite(b) and b > cv:
            out[sym] = b
    return out
