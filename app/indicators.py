"""Chi bao — giu DUNG dinh nghia cua ban nghien cuu, khong 'cai tien'.

Hai cho de sai, da tung sai mot lan trong kho nay:
  - ATR o day la SMA cua True Range, KHONG phai RMA cua Wilder.
  - MA la SMA.
Doi bat ky cai nao la ket qua live lech khoi backtest ma khong ai biet vi sao.
"""
from __future__ import annotations

import numpy as np


def sma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        c = np.concatenate([[0.0], np.cumsum(x)])
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def rsi(x: np.ndarray, n: int = 2) -> np.ndarray:
    """RSI Wilder — CHEP NGUYEN tu scripts/strategy_backtest.py.

    Da thu viet lai bang SMA cho gon va no lech 397/397 diem. Ban nghien cuu
    dung trung binh truot Wilder voi mam la trung binh n gia tri dau; bat ky
    bien the nao khac deu cho nguong RSI(2)<10 roi vao nhung ngay khac.
    """
    d = np.diff(x, prepend=x[0])
    up, dn = np.maximum(d, 0.0), np.maximum(-d, 0.0)
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    au = float(np.mean(up[1:n + 1]))
    ad = float(np.mean(dn[1:n + 1]))
    for i in range(n + 1, len(x)):
        au = (au * (n - 1) + up[i]) / n
        ad = (ad * (n - 1) + dn[i]) / n
        out[i] = 100.0 if ad == 0 else 100 - 100 / (1 + au / max(ad, 1e-12))
    return out


def true_range(h, l, c) -> np.ndarray:
    pc = np.concatenate([[np.nan], c[:-1]])
    a = h - l
    b = np.abs(h - pc)
    d = np.abs(l - pc)
    return np.nanmax(np.vstack([a, b, d]), axis=0)


def atr(h, l, c, n: int = 14) -> np.ndarray:
    return sma(true_range(h, l, c), n)


def trailing_median(x: np.ndarray, n: int = 30) -> np.ndarray:
    """Trung vi TRUOT n ngay, tinh den chinh nen do. Nhan qua."""
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        w = np.lib.stride_tricks.sliding_window_view(x, n)
        out[n - 1:] = np.median(w, axis=1)
    return out
