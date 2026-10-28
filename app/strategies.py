"""Hai chien luoc, sinh SO MUC TIEU cho ngay hom nay.

Cho nay phai bam sat hai tai lieu da chot:
  docs/rsi2-connors.md       — RSI(2) Connors v2
  docs/xsmom-volnorm.md      — dong luong cat ngang chia bien dong

Quy uoc thoi gian quan trong: tin hieu chot tren nen 1D DA DONG luc 00:00 UTC,
va khop o OPEN cua nen ke tiep — tuc ngay sau khi luot chay ket thuc. Vi the
lich chay dat 00:05 UTC: chay xong la khop luon, dung bang backtest.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from . import indicators as I
from . import settings
from .binance import DAY


def prep(bars: dict) -> dict:
    """Tinh san chi bao cho moi ma, mot lan moi luot chay."""
    R, X = settings.strat()
    out = {}
    for sym, b in bars.items():
        n = len(b["c"])
        if n < R["min_bars"]:
            continue
        d = dict(b)
        d["rsi"] = I.rsi(b["c"], 2)
        d["ma20"] = I.sma(b["c"], R["ma"])
        d["atr"] = I.atr(b["h"], b["l"], b["c"], R["atr"])
        d["dvt"] = I.trailing_median(b["c"] * b["v"], 30)
        # MA rieng cua dong luong — do dai khac MA cua RSI(2)
        d["xma"] = I.sma(b["c"], X["ma"]) if X.get("ma") else None
        out[sym] = d
    return out


def ranks_on(P: dict, day: int) -> dict:
    """Hang thanh khoan CHEO cua ngay `day` (1 = cao nhat). Hoan toan nhan qua."""
    vals = []
    for sym, d in P.items():
        j = int(np.searchsorted(d["t"], day))
        if j >= len(d["t"]) or d["t"][j] != day:
            continue
        v = d["dvt"][j]
        if np.isfinite(v):
            vals.append((v, sym))
    vals.sort(reverse=True)
    return {s: i + 1 for i, (_, s) in enumerate(vals)}


def _idx(d: dict, day: int) -> int | None:
    j = int(np.searchsorted(d["t"], day))
    return j if j < len(d["t"]) and d["t"][j] == day else None


# ------------------------------------------------------------------ RSI(2)
def rsi2_signals(P: dict, rank: dict, day: int, held: dict,
                 nobuy: dict | None = None) -> list:
    """Cac ma DU DIEU KIEN vao lenh hom nay, xep theo RSI tang dan.

    `held` = so lop dang giu moi ma. Ma da du `layers` lop thi bo qua; ma dang
    giu it hon thi tin hieu hom nay la mot lop MUA THEM.

    Chua ap gioi han cho — book.py quyet dinh lay bao nhieu, vi so cho con
    lai phu thuoc vi the dang mo. `nobuy` = ma co thong bao huy niem yet
    (app/delist.py): bo truoc khi xep, cho trong nhuong cho tin hieu ke tiep.
    """
    R, _ = settings.strat()
    out = []
    for sym, d in P.items():
        if held.get(sym, 0) >= R.get("layers", 1) or rank.get(sym, 10**9) > R["topn"]:
            continue
        if nobuy and sym in nobuy:
            continue
        # KHONG duoc doi hoi ton tai nen j+1. Backtest khop o open nen ke
        # tiep nen no can nen do trong du lieu; chay that thi nen ke tiep
        # CHUA TON TAI — ta dang dung o dau no, va khop ngay bay gio. Dieu
        # kien thua nay tung lam moi tin hieu cua ngay hom nay bien mat.
        j = _idx(d, day)
        if j is None:
            continue
        r, m, a = d["rsi"][j], d["ma20"][j], d["atr"][j]
        if not (np.isfinite(r) and r < R["rsi_in"]):
            continue
        if not (np.isfinite(m) and d["c"][j] > m):
            continue
        if not np.isfinite(a):
            continue
        out.append({"symbol": sym, "rsi": float(r), "atr": float(a),
                    "close": float(d["c"][j]), "rank": rank.get(sym)})
    out.sort(key=lambda x: x["rsi"])
    return out


def rsi2_exits(P: dict, day: int, positions: list) -> list:
    """Vi the RSI(2) can dong hom nay: cham stop (trong ngay) hoac RSI > 70."""
    R, _ = settings.strat()
    out = []
    for p in positions:
        d = P.get(p["symbol"])
        if d is None:
            out.append((p, "hết dữ liệu"))
            continue
        j = _idx(d, day)
        if j is None:
            out.append((p, "hết dữ liệu"))
            continue
        if p["stop"] and d["l"][j] <= p["stop"]:
            out.append((p, "cắt lỗ"))
        elif np.isfinite(d["rsi"][j]) and d["rsi"][j] > R["rsi_out"]:
            out.append((p, "RSI>70"))
    return out


def rsi2_stop(px: float, atr: float) -> float:
    R, _ = settings.strat()
    return max(px - R["atr_k"] * atr, px * (1 - R["cap"]))


# ----------------------------------------------------- dong luong cat ngang
def xsmom_sleeve_of(day: int, epoch: int) -> int:
    """So nao tai can bang hom nay. Cac so lech nhau dung mot ngay."""
    _, X = settings.strat()
    return int(((day - epoch) // DAY) % X["sleeves"])


def xsmom_target(P: dict, rank: dict, day: int, nobuy: dict | None = None) -> list | None:
    """Bon vi the moi cho so dang den luot: 2 mua diem cao nhat, 2 ban thap nhat."""
    _, X = settings.strat()
    L = X["lookback"]
    sc = []
    for sym, d in P.items():
        if rank.get(sym, 10**9) > X["topn"]:
            continue
        j = _idx(d, day)
        if j is None or j - L < 0:        # xem ghi chu o rsi2_signals
            continue
        c = d["c"]
        if c[j - L] <= 0 or not np.isfinite(c[j]):
            continue
        lg = np.log(c[j - L + 1:j + 1] / c[j - L:j])
        vol = float(np.nanstd(lg))
        if not np.isfinite(vol) or vol <= 0:
            continue
        ret = float(c[j] / c[j - L] - 1)
        sc.append((ret / vol, sym, vol, j))
    if len(sc) < 10:
        return None
    sc.sort(reverse=True, key=lambda x: x[0])
    k = max(X["legs"], int(len(sc) * X["frac"]))

    def ok(sym: str, j: int, side: int) -> bool:
        """Loc xu huong: chi MUA tren MA, chi BAN duoi MA. Tat thi luon dung.

        Ma co thong bao huy niem yet thi khong MUA (bo han, giong loc MA);
        chan BAN giu nguyen."""
        if side > 0 and nobuy and sym in nobuy:
            return False
        if not X.get("ma"):
            return True
        m = P[sym].get("xma")
        if m is None or not np.isfinite(m[j]):
            return False
        c = float(P[sym]["c"][j])
        return c > float(m[j]) if side > 0 else c < float(m[j])

    # `vol` di kem de ben ngoai tinh duoc rui ro mot ky: sigma x sqrt(so ngay
    # giu). Day la mau so R cua chien luoc nay (khong co stop).
    # Ung vien khong qua loc thi BO HAN, khong thay bang ma ke tiep: thay the
    # la mot luat khac han, va ban do chua duoc kiem chung.
    return ([{"symbol": s, "side": 1, "score": v, "vol": g}
             for v, s, g, j in sc[:k] if ok(s, j, 1)]
            + [{"symbol": s, "side": -1, "score": v, "vol": g}
               for v, s, g, j in sc[-k:] if ok(s, j, -1)])
