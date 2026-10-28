"""Cat lo RSI(2) o dinh khoi luong (HVN) gan nhat duoi gia.

CHEP DUNG dinh nghia cua scripts/vp_stops.py (docs/stop-dinh-day.md § Volume
profile) — doi bat ky buoc nao la lech khoi ket qua nghien cuu:
  - nen 1H cua `days` ngay TRUOC moc close nen D da dong
  - khoi luong USD (close × volume) dat vao gia dien hinh (h+l+c)/3
  - o rong `binw` × ATR14 ngay, bat dau tu gia dien hinh thap nhat
  - lam muot [1/4, 1/2, 1/4], bien lap lai o ngoai cung
  - HVN = o >= hai o ke VA >= trung binh profile; lay HVN GAN gia nhat trong
    so nam duoi gia − 0,1 × ATR
Khong du nen (< days × 12) hoac khong co HVN → None: nguoi goi dung 6×ATR.
"""
from __future__ import annotations

import numpy as np

from .binance import DAY, PublicApi


def level(t, tp, v, t_end, px, atr, days, binw):
    a, b = np.searchsorted(t, [t_end - days * DAY, t_end])
    if b - a < days * 12 or not np.isfinite(atr) or atr <= 0:
        return None
    x, w = tp[a:b], v[a:b]
    lo = x.min()
    nb = max(3, int(np.ceil((x.max() - lo) / (binw * atr))) + 1)
    hist, edges = np.histogram(x, bins=nb, range=(lo, lo + nb * binw * atr), weights=w)
    hs = np.convolve(np.pad(hist, 1, mode="edge"), [0.25, 0.5, 0.25], "valid")
    ctr = (edges[:-1] + edges[1:]) / 2
    pk = np.zeros(len(hs), bool)
    pk[1:-1] = (hs[1:-1] >= hs[:-2]) & (hs[1:-1] >= hs[2:]) & (hs[1:-1] >= hs.mean())
    idx = np.flatnonzero(pk & (ctr < px - 0.1 * atr))
    if not len(idx):
        return None
    return float(ctr[idx[np.argmin(np.abs(ctr[idx] - px))]])


def hvn_below(sym: str, t_end: int, px: float, atr: float, days: int,
              binw: float, api: PublicApi | None = None) -> float | None:
    """Tai nen 1H tu san va tra muc HVN. Loi mang → None (dung stop ATR)."""
    own = api is None
    api = api or PublicApi()
    try:
        rows = api.klines_1h(sym, t_end - days * DAY, limit=min(1500, days * 24 + 5))
    finally:
        if own:
            api.close()
    if not rows:
        return None
    k = np.array([[float(r[0]), float(r[2]), float(r[3]), float(r[4]), float(r[5])]
                  for r in rows])
    t = k[:, 0].astype(np.int64)
    keep = t < t_end
    k, t = k[keep], t[keep]
    if not len(t):
        return None
    tp = (k[:, 1] + k[:, 2] + k[:, 3]) / 3
    return level(t, tp, k[:, 3] * k[:, 4], t_end, px, atr, days, binw)
