"""Thuc te so voi backtest — chi so cap bot va cap chien luoc (bang dieu khien).

Y tuong: bot moi chay d ngay thi KHONG nhan thang len 1 nam. Thay vao do hoi
"neu bot chay d ngay bat ky trong backtest 2021–26 thi chi so X nam trong
khoang nao?" — lay MOI cua so d ngay lien tiep cua chuoi lai/lo ngay backtest
(he so dang chay, co tran hoac khong tran) → phan vi 2,5 / 50 / 97,5. Chi so
thuc te nam ngoai khoang 95% thi gan nhan lech.

Cap chien luoc: so lenh (cua so d ngay tren chuoi lenh mo / ngay), ti le thang
(nhi thuc voi so lenh thuc te) va R/lenh (TB ± 1,96 sd/√n tu phan phoi R tung
lenh backtest, methods_bt.json r_stats).
"""
from __future__ import annotations

import numpy as np

K = ("xsmom", "rsi2", "tsvw", "dsrm", "c13", "vsa")
_CACHE: dict = {}


def bt_daily(bt: dict, alloc: dict, ru: float, ck: str, r_frac: float) -> dict:
    n = bt["n"]
    d = np.zeros(n); g = np.zeros(n); npos = np.zeros(n); per = {}
    for k in K:
        a = float(alloc.get(k, 0.0))
        if a <= 0 or k not in bt["series"]:
            continue
        s = np.asarray(bt["series"][k], float)
        parts = (ck or "").split("+")      # "kb+tp+wf": combo Kase/funding/BSADF + chuoi chot loi / windfall
        ck0, tp, wf = parts[0], "tp" in parts[1:], "wf" in parts[1:]
        if k == "xsmom" and ck0 and ck0 in bt.get("pp1x_combo", {}):
            s = s + np.asarray(bt["pp1x_combo"][ck0], float)
        if k == "xsmom" and tp and "pp1tp" in bt["series"]:
            s = s + np.asarray(bt["series"]["pp1tp"], float)
        if k == "xsmom" and wf and "pp1wf" in bt["series"]:
            s = s + np.asarray(bt["series"]["pp1wf"], float)
        if k == "vsa":
            s = s / (100 * r_frac)
        d += s * ru * a
        if bt.get("gross"):
            g += np.asarray(bt["gross"][k], float) * ru * a
            npos += np.asarray(bt["npos"][k], float)
        per[k] = np.asarray(bt.get("nopen", {}).get(k, [0] * n), float)
    return {"d": d, "g": g, "npos": npos, "nopen": per}


def _win_sums(x: np.ndarray, L: int) -> np.ndarray:
    c = np.concatenate(([0.0], np.cumsum(x)))
    return c[L:] - c[:-L]


def window_metrics(x: np.ndarray, L: int) -> dict:
    """Moi chi so tren moi cua so L ngay lien tiep cua chuoi lai/lo ngay x."""
    n = len(x)
    L = max(1, min(L, n))
    s1 = _win_sums(x, L)
    out = {"pnl": s1, "per_year": s1 / L * 365}
    s2 = _win_sums(x * x, L)
    if L >= 7:
        mu = s1 / L
        sd = np.sqrt(np.maximum(s2 / L - mu * mu, 1e-18))
        out["sharpe"] = mu / sd * np.sqrt(365)
    out["win_days"] = _win_sums((x > 0).astype(float), L) / L
    dd = np.empty(n - L + 1); worst = np.empty(n - L + 1)
    for i in range(n - L + 1):
        w = x[i:i + L]
        c = np.cumsum(w)
        pk = np.maximum.accumulate(np.maximum(c, 0.0))
        dd[i] = (pk - c).max()
        worst[i] = w.min()
    out["max_dd"] = dd
    out["worst_day"] = worst
    return out


def q3(a: np.ndarray) -> list:
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 50)), float(np.percentile(a, 97.5))]


def compare(bt: dict, key: tuple, alloc: dict, ru: float, ck: str, r_frac: float, cap_usd: float,
            act: dict, L: int, strat_act: dict) -> dict:
    """act: chuoi thuc te {"d": lai/lo ngay, "g": phoi nhiem, "npos": so vi the}; strat_act: {k: {n, win, r_per}}."""
    ck_ = (key, L)
    if ck_ not in _CACHE:
        B = bt_daily(bt, alloc, ru, ck, r_frac)
        res = {}
        for mode in ("cap", "raw"):
            x = B["d"] if mode == "raw" else np.where(B["g"] > cap_usd, B["d"] * cap_usd / np.maximum(B["g"], 1e-9), B["d"])
            res[mode] = {k: q3(v) for k, v in window_metrics(x, L).items()}
        res["gross"] = q3(_win_sums(np.minimum(B["g"], cap_usd), L) / L)
        res["gross_raw"] = q3(_win_sums(B["g"], L) / L)
        res["npos"] = q3(_win_sums(B["npos"], L) / L)
        res["n_trades"] = {k: q3(_win_sums(v, L)) for k, v in B["nopen"].items()}
        if len(_CACHE) > 40:
            _CACHE.clear()
        _CACHE[ck_] = res
    res = _CACHE[ck_]
    # chi so thuc te tren dung chuoi da chay
    x = np.asarray(act["d"], float)
    A = {}
    if len(x):
        c = np.cumsum(x)
        A["pnl"] = float(c[-1])
        A["per_year"] = float(c[-1] / max(L, 1) * 365)
        A["max_dd"] = float((np.maximum.accumulate(np.maximum(c, 0.0)) - c).max())
        A["worst_day"] = float(x.min())
        A["win_days"] = float((x > 0).mean())
        if len(x) >= 7 and x.std() > 0:
            A["sharpe"] = float(x.mean() / x.std() * np.sqrt(365))
    if act.get("g"):
        A["gross"] = float(np.mean(act["g"]))
    if act.get("npos"):
        A["npos"] = float(np.mean(act["npos"]))
    st = {}
    rs = bt.get("r_stats", {})
    for k, a in strat_act.items():
        n = a.get("n") or 0
        ci = {"n_trades": res["n_trades"].get(k)}
        r = rs.get(k)
        if r and n:
            p = r["win"]; h = 1.96 * np.sqrt(p * (1 - p) / n)
            ci["win"] = [max(0.0, p - h), p, min(1.0, p + h)]
            h = 1.96 * r["sd"] / np.sqrt(n)
            ci["r_per"] = [r["mean"] - h, r["mean"], r["mean"] + h]
        st[k] = ci
    return {"L": L, "bt": res, "act": A, "strat": st}
