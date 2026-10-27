"""Tinh lai lich su theo DUNG cach bot chay, voi bo tham so tuy chon.

Khac ban nghien cuu o cho no mo phong CO CHE CUA APP chu khong phai mo hinh
ly tuong:
  - tin hieu chot tren nen 1D da dong, khop o OPEN nen ke tiep (luot 00:05)
  - RSI(2) cham stop hay RSI > nguong thi dong o open HOM SAU — bot khong
    dat lenh dung tren san, no doc nen da dong roi moi dong
  - dong luong: vi the trung (chien luoc, so, ma, chieu) giu nguyen, khong
    mua ban lai, khong ton phi — dung executor.plan()
  - tran rui ro ap theo dung thu tu executor.apply_caps(), cong them hai
    chan cua san: muc toi thieu moi lenh va ky quy (phoi nhiem / don bay
    khong vuot von)
  - lai/lo cong theo USD voi 1R co dinh, funding tinh tung ngay

Vu tru: ma du `rsi2.min_bars` nen TINH DEN NGAY DO (khong nhin truoc), xep
hang thanh khoan cheo trong chinh nhom do — giong ranks_on() cua app.
"""
from __future__ import annotations

import threading
import time
import warnings
from datetime import datetime, timezone

import numpy as np

from . import data, db, settings
from . import indicators as I
from .binance import DAY
from .config import CFG, FEE_BPS

_LOCK = threading.Lock()
_CACHE: dict = {"key": None}


# ---------------------------------------------------------------- du lieu
def _key():
    cx = db.connect()
    try:
        a = cx.execute("SELECT COUNT(*), MAX(ts) FROM bars").fetchone()
        b = cx.execute("SELECT COUNT(*), MAX(ts) FROM funding").fetchone()
        return tuple(a) + tuple(b)
    finally:
        cx.close()


def _load() -> dict:
    """Ma tran ma x ngay tren luoi ngay chung. Cache theo dau van kho."""
    k = _key()
    if _CACHE["key"] == k:
        return _CACHE["D"]
    bars = data.load_all(30)
    bars = {s: b for s, b in bars.items() if data.is_crypto(b)}
    syms = sorted(bars)
    T = np.array(sorted({int(t) for b in bars.values() for t in b["t"]}), np.int64)
    n, m = len(syms), len(T)
    O, H, L, C = (np.full((n, m), np.nan) for _ in range(4))
    AGE = np.zeros((n, m), np.int32)
    RSI = np.full((n, m), np.nan)
    DVT = np.full((n, m), np.nan)
    for i, s in enumerate(syms):
        b = bars[s]
        j = np.searchsorted(T, b["t"])
        O[i, j], H[i, j], L[i, j], C[i, j] = b["o"], b["h"], b["l"], b["c"]
        AGE[i, j] = np.arange(1, len(j) + 1)
        RSI[i, j] = I.rsi(b["c"], 2)
        DVT[i, j] = I.trailing_median(b["c"] * b["v"], 30)
    # funding cong theo ngay UTC
    FD = np.zeros((n, m))
    ix = {s: i for i, s in enumerate(syms)}
    cx = db.connect()
    cx.row_factory = None              # 2,6 trieu dong: tuple tran nhanh hon Row
    try:
        rows = cx.execute("SELECT symbol, ts, rate FROM funding").fetchall()
    finally:
        cx.close()
    si = np.array([ix.get(r[0], -1) for r in rows])
    ts = np.array([r[1] for r in rows], np.int64)
    rt = np.array([r[2] for r in rows], float)
    ok = si >= 0
    dj = np.searchsorted(T, (ts[ok] // DAY) * DAY)
    good = (dj < m)
    dj, s_, r_ = dj[good], si[ok][good], rt[ok][good]
    good = T[dj] == (ts[ok][good] // DAY) * DAY
    np.add.at(FD, (s_[good], dj[good]), r_[good])
    with np.errstate(invalid="ignore", divide="ignore"):
        LG = np.log(C[:, 1:] / C[:, :-1])
    D = {"syms": syms, "T": T, "O": O, "H": H, "L": L, "C": C, "AGE": AGE,
         "RSI": RSI, "DVT": DVT, "FD": FD, "LG": LG, "ranks": {}}
    _CACHE.update(key=k, D=D)
    return D


def _sma(X: np.ndarray, n: int) -> np.ndarray:
    """SMA theo hang; cua so co o trong thi NaN — trung I.sma tren chuoi lien."""
    F = np.isfinite(X)
    Z = np.concatenate([np.zeros((X.shape[0], 1)), np.cumsum(np.where(F, X, 0), 1)], 1)
    N = np.concatenate([np.zeros((X.shape[0], 1)), np.cumsum(F, 1)], 1)
    out = np.full(X.shape, np.nan)
    if X.shape[1] >= n:
        s = Z[:, n:] - Z[:, :-n]
        c = N[:, n:] - N[:, :-n]
        out[:, n - 1:] = np.where(c == n, s / n, np.nan)
    return out


def _atr(D: dict, n: int) -> np.ndarray:
    pc = np.concatenate([np.full((D["C"].shape[0], 1), np.nan), D["C"][:, :-1]], 1)
    with np.errstate(invalid="ignore"):
        tr = np.fmax(np.fmax(D["H"] - D["L"], np.abs(D["H"] - pc)),
                     np.abs(D["L"] - pc))
    tr[~np.isfinite(D["H"])] = np.nan
    return _sma(tr, n)


def _ranks(D: dict, min_bars: int) -> np.ndarray:
    """Hang thanh khoan cheo moi ngay trong nhom du nen. 1 = cao nhat."""
    if min_bars in D["ranks"]:
        return D["ranks"][min_bars]
    V = np.where(D["AGE"] >= min_bars, D["DVT"], np.nan)
    RK = np.full(V.shape, np.inf)
    for j in range(V.shape[1]):
        ok = np.flatnonzero(np.isfinite(V[:, j]))
        if len(ok):
            RK[ok[np.argsort(-V[ok, j])], j] = np.arange(1, len(ok) + 1)
    D["ranks"][min_bars] = RK
    return RK


# ---------------------------------------------------------------- tham so
EXTRA = {
    "start_equity": (float, 1.0, 1e9, "vốn ban đầu (USD)"),
    "leverage": (float, 1.0, 125.0, "đòn bẩy — ký quỹ = phơi nhiễm ÷ đòn bẩy"),
    "min_notional": (float, 0.0, 1e6, "giá trị lệnh tối thiểu của sàn (USD)"),
    "fee_bps": (float, 0.0, 200.0, "phí khứ hồi mỗi lệnh (bps)"),
}


def defaults() -> dict:
    e = settings.effective()
    e.update(start_equity=CFG.start_equity, leverage=float(CFG.leverage),
             min_notional=5.0, fee_bps=FEE_BPS, one_way=True)
    return e


def _params(body: dict) -> dict:
    patch = {k: v for k, v in body.items() if k in settings.SPEC}
    out = defaults()
    out.update(settings.validate(patch))       # kiem kieu, khoang, so = ngay giu
    for k, (typ, lo, hi, desc) in EXTRA.items():
        if k in body:
            try:
                v = typ(body[k])
            except (TypeError, ValueError):
                raise ValueError(f"«{desc}» phải là số")
            if not (lo <= v <= hi):
                raise ValueError(f"«{desc}» phải nằm trong [{lo}, {hi}], nhận {v}")
            out[k] = v
    out["one_way"] = bool(body.get("one_way", True))
    for k in ("start", "end"):
        v = body.get(k)
        if v:
            try:
                out[k] = int(datetime.strptime(str(v), "%Y-%m-%d")
                             .replace(tzinfo=timezone.utc).timestamp() * 1000)
            except ValueError:
                raise ValueError(f"ngày «{v}» phải có dạng YYYY-MM-DD")
        else:
            out[k] = None
    return out


# ---------------------------------------------------------------- mo phong
def run(body: dict) -> dict:
    if not _LOCK.acquire(blocking=False):
        raise RuntimeError("đang có một phép tính khác chạy — đợi nó xong")
    try:
        return _run(_params(body or {}))
    finally:
        _LOCK.release()


def _run(p: dict) -> dict:
    t0 = time.time()
    D = _load()
    T, O, H, Lo, C = D["T"], D["O"], D["H"], D["L"], D["C"]
    syms, FD, LG, RSI, AGE = D["syms"], D["FD"], D["LG"], D["RSI"], D["AGE"]
    n, m = C.shape
    if m < 3:
        raise ValueError("kho nến rỗng — bấm «Tải dữ liệu» trước")
    R = {k[5:]: v for k, v in p.items() if k.startswith("rsi2.")}
    X = {k[6:]: v for k, v in p.items() if k.startswith("xsmom.")}
    RK = _ranks(D, int(R["min_bars"]))
    MA = _sma(C, int(R["ma"]))
    ATR = _atr(D, int(R["atr"]))
    XMA = _sma(C, int(X["ma"])) if X["ma"] else None
    r_rsi2 = p["risk_r_usd"] * p["alloc_rsi2"]
    r_x = p["risk_r_usd"] * p["alloc_xsmom"]
    fee = p["fee_bps"] / 1e4
    lev, eq0 = p["leverage"], p["start_equity"]
    epoch = int(T[0])
    Lb, hold = int(X["lookback"]), int(X["hold"])

    # bat dau tu ngay dau tien co ma du nen — truoc do khong chien luoc nao
    # vao duoc lenh, de vao chi keo dai duong von phang va ha CAGR
    warm = int(np.argmax((AGE >= R["min_bars"]).any(axis=0)))
    j0 = max(1, warm, int(np.searchsorted(T, p["start"])) if p["start"] else 1)
    j1 = min(m - 2, int(np.searchsorted(T, p["end"], "right")) - 1
             if p["end"] else m - 2)
    if j1 <= j0:
        raise ValueError("khoảng ngày không có nến nào")

    pos: list = []                 # vi the dang mo
    trades: list = []
    blocked: dict = {}
    real = {"rsi2": 0.0, "xsmom": 0.0}
    curve = []                     # (ts, von, lai luy ke rsi2, lai luy ke xsmom)
    peak_g = peak_mu = 0.0
    nopen_sum = 0
    dead = False

    def last_px(si, j):
        """Gia gan nhat <= j — dung cho ma bi huy giua chung."""
        c = C[si, :j + 1]
        f = np.flatnonzero(np.isfinite(c))
        return float(c[f[-1]]) if len(f) else np.nan

    def block(a, why):
        key = (a["strategy"], why)
        blocked[key] = blocked.get(key, 0) + 1

    for j in range(j0, j1 + 1):
        # ---- funding cua ngay j cho vi the dang mo (khop truoc ngay j) ----
        for q in pos:
            f = FD[q["si"], j] * q["notional"] * q["side"]
            q["fund"] += f
            real[q["strategy"]] -= f

        # ---- RSI(2): thoat, doc nen j da dong ----
        closes = []
        for q in pos:
            if q["strategy"] != "rsi2":
                continue
            si = q["si"]
            if not np.isfinite(C[si, j]):
                closes.append((q, "hết dữ liệu"))
            elif q["stop"] and Lo[si, j] <= q["stop"]:
                closes.append((q, "cắt lỗ"))
            elif np.isfinite(RSI[si, j]) and RSI[si, j] > R["rsi_out"]:
                closes.append((q, f"RSI>{R['rsi_out']:g}"))
        cset = {id(q) for q, _ in closes}
        opens = []
        uni = (AGE[:, j] >= R["min_bars"]) & np.isfinite(C[:, j])

        # ---- RSI(2): vao ----
        if r_rsi2 > 0:
            # lop dang giu moi ma — giong runner.build_target()
            held: dict = {}
            for q in pos:
                if q["strategy"] == "rsi2" and id(q) not in cset:
                    held.setdefault(q["si"], set()).add(q["sleeve"] or 0)
            free = int(R["slots"]) - sum(len(v) for v in held.values())
            if free > 0:
                with np.errstate(invalid="ignore"):
                    ok = (uni & (RK[:, j] <= R["topn"]) & (RSI[:, j] < R["rsi_in"])
                          & (C[:, j] > MA[:, j]) & np.isfinite(ATR[:, j]))
                cand = [int(si) for si in np.flatnonzero(ok)
                        if len(held.get(si, ())) < R.get("layers", 1)]
                cand.sort(key=lambda si: RSI[si, j])
                for si in cand[:free]:
                    c = float(C[si, j])
                    stop = max(c - R["atr_k"] * float(ATR[si, j]), c * (1 - R["cap"]))
                    rf = (c - stop) / c
                    used = held.get(si, set())
                    k = next(i for i in range(len(used) + 1) if i not in used)
                    if rf > 0:
                        opens.append({"strategy": "rsi2", "sleeve": k or None,
                                      "si": si, "side": 1, "stop": stop,
                                      "r_usd": r_rsi2, "notional": r_rsi2 / rf})
        elif any(q["strategy"] == "rsi2" for q in pos):
            closes += [(q, "chiến lược tắt") for q in pos
                       if q["strategy"] == "rsi2" and id(q) not in cset]

        # ---- dong luong: so den luot ----
        sl = int(((int(T[j]) - epoch) // DAY) % int(X["sleeves"]))
        old = [q for q in pos if q["strategy"] == "xsmom" and q["sleeve"] == sl]
        if r_x <= 0:
            old = [q for q in pos if q["strategy"] == "xsmom"]
        new = []
        if r_x > 0 and j - Lb >= 0:
            elig = uni & (RK[:, j] <= X["topn"]) & (AGE[:, j] >= X["min_bars"])
            with np.errstate(invalid="ignore", divide="ignore"), \
                    warnings.catch_warnings():
                # ma chua niem yet: ca cua so NaN — bi loai ngay ben duoi
                warnings.simplefilter("ignore", RuntimeWarning)
                ret = C[:, j] / C[:, j - Lb] - 1
                vol = np.nanstd(LG[:, j - Lb:j], axis=1)
                sc = ret / vol
            elig &= np.isfinite(sc) & (vol > 0) & (C[:, j - Lb] > 0)
            idx = np.flatnonzero(elig)
            if len(idx) >= 10:
                order = idx[np.argsort(-sc[idx], kind="stable")]
                k = max(int(X["legs"]), int(len(idx) * X["frac"]))
                for si, side in ([(s, 1) for s in order[:k]]
                                 + [(s, -1) for s in order[-k:]]):
                    if XMA is not None:
                        mv = XMA[si, j]
                        if not np.isfinite(mv):
                            continue
                        if (side > 0 and not C[si, j] > mv) or \
                           (side < 0 and not C[si, j] < mv):
                            continue
                    rf = float(vol[si]) * np.sqrt(hold)
                    if rf > 0:
                        new.append({"strategy": "xsmom", "sleeve": sl, "si": int(si),
                                    "side": side, "stop": None, "r_usd": r_x,
                                    "notional": r_x / rf})
        keep = {(q["si"], q["side"]) for q in old}
        want = {(a["si"], a["side"]) for a in new}
        closes += [(q, "tái cân bằng" if r_x > 0 else "chiến lược tắt") for q in old
                   if (q["si"], q["side"]) not in want and id(q) not in cset]
        opens += [a for a in new if (a["si"], a["side"]) not in keep]

        # ---- tran: dung thu tu executor.plan() + apply_caps() ----
        cids = {id(q) for q, _ in closes}
        opens.sort(key=lambda a: syms[a["si"]])
        if p["one_way"]:
            side_of: dict = {}
            for q in pos:
                if id(q) not in cids:
                    side_of.setdefault(q["si"], q["side"])
            ok1 = []
            for a in opens:
                h_ = side_of.get(a["si"])
                if h_ is not None and h_ != a["side"]:
                    block(a, "ngược chiều trên cùng mã (sàn một chiều)")
                    continue
                side_of.setdefault(a["si"], a["side"])
                ok1.append(a)
            opens = ok1
        live = len(pos) - len(closes)
        gross_run = 0.0
        n_run = 0
        held_g = sum(q["notional"] for q in pos if id(q) not in cids)
        eq_now = curve[-1][1] if curve else eq0
        ok2 = []
        for a in opens:
            px = O[a["si"], j + 1]
            if not np.isfinite(px) or px <= 0:
                block(a, "không có giá")
                continue
            nt = a["notional"]
            if live + n_run >= p["risk_max_open"]:
                block(a, f"đủ {p['risk_max_open']} lệnh mở")
                continue
            if nt > p["max_order_usd"]:
                block(a, f"vượt trần lệnh {p['max_order_usd']:g} USD")
                continue
            if gross_run + nt > p["max_gross_usd"]:
                block(a, f"vượt trần tổng lượt {p['max_gross_usd']:g} USD")
                continue
            if n_run >= p["max_orders_per_run"]:
                block(a, "vượt số lệnh mỗi lượt")
                continue
            gross_run += nt
            n_run += 1
            # hai chan cua san, sau khi qua tran cua app
            if nt < p["min_notional"]:
                block(a, "dưới mức tối thiểu của sàn")
                continue
            if (held_g + nt) / lev > eq_now:
                block(a, "thiếu ký quỹ")
                continue
            held_g += nt
            ok2.append({**a, "entry_px": float(px), "entry_j": j + 1, "fund": 0.0})

        # ---- khop o open j+1 ----
        for q, why in closes:
            si = q["si"]
            px = O[si, j + 1]
            if not np.isfinite(px) or px <= 0:
                px = last_px(si, j)
            g = q["notional"] * q["side"] * (px / q["entry_px"] - 1)
            pnl = g - q["notional"] * fee
            real[q["strategy"]] += pnl
            trades.append({"s": q["strategy"], "sym": syms[si], "side": q["side"],
                           "sl": q["sleeve"], "a": int(T[q["entry_j"]]),
                           "z": int(T[j + 1]), "pin": q["entry_px"], "pout": float(px),
                           "usd": q["notional"], "r": q["r_usd"],
                           "pnl": pnl - q["fund"], "fund": q["fund"], "why": why})
        pos = [q for q in pos if id(q) not in cids] + ok2

        # ---- danh gia lai o close j+1 ----
        un = {"rsi2": 0.0, "xsmom": 0.0}
        g_ = 0.0
        for q in pos:
            c = C[q["si"], j + 1]
            if not np.isfinite(c):
                c = last_px(q["si"], j + 1)
            un[q["strategy"]] += q["notional"] * q["side"] * (c / q["entry_px"] - 1)
            g_ += q["notional"]
        e = eq0 + real["rsi2"] + real["xsmom"] + un["rsi2"] + un["xsmom"]
        curve.append((int(T[j + 1]), e, real["rsi2"] + un["rsi2"],
                      real["xsmom"] + un["xsmom"]))
        peak_g = max(peak_g, g_)
        if e > 0:
            peak_mu = max(peak_mu, g_ / lev / e)
        nopen_sum += len(pos)
        if e <= 0:
            dead = True
            break

    return _report(p, curve, trades, blocked, pos, peak_g, peak_mu,
                   nopen_sum, dead, time.time() - t0, D)


# ---------------------------------------------------------------- bao cao
def _dd(v: np.ndarray):
    pk = np.maximum.accumulate(v)
    dd_usd = pk - v
    with np.errstate(invalid="ignore", divide="ignore"):
        dd_pc = np.where(pk > 0, dd_usd / pk, 0.0)
    best = cur = 0
    for u in dd_usd > 1e-9:
        cur = cur + 1 if u else 0
        best = max(best, cur)
    return float(dd_usd.max()), float(dd_pc.max()), best


def _yr(ms: int) -> int:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).year


def _report(p, curve, trades, blocked, pos, peak_g, peak_mu, nopen_sum,
            dead, secs, D) -> dict:
    if not curve:
        raise ValueError("không có ngày nào để tính")
    eq0 = p["start_equity"]
    ts = np.array([c[0] for c in curve], np.int64)
    ev = np.array([c[1] for c in curve])
    yrs = max((ts[-1] - ts[0]) / DAY / 365.25, 1e-9)
    dd_usd, dd_pc, under = _dd(np.concatenate([[eq0], ev]))
    end = float(ev[-1])
    cagr = (end / eq0) ** (1 / yrs) - 1 if end > 0 else -1.0

    per = {}
    for s in ("rsi2", "xsmom"):
        tr = [t for t in trades if t["s"] == s]
        rr = np.array([t["pnl"] / t["r"] for t in tr if t["r"]]) if tr else np.array([])
        hd = np.array([(t["z"] - t["a"]) / DAY for t in tr]) if tr else np.array([])
        cum = np.array([c[2 if s == "rsi2" else 3] for c in curve])
        sd_usd, _, sd_under = _dd(np.concatenate([[0.0], cum]))
        per[s] = {"trades": len(tr),
                  "win": float(np.mean([t["pnl"] > 0 for t in tr])) if tr else None,
                  "avg_r": float(rr.mean()) if len(rr) else None,
                  "pnl": float(cum[-1]), "fund": float(sum(t["fund"] for t in tr)),
                  "hold": float(hd.mean()) if len(hd) else None,
                  "dd_usd": sd_usd, "under": sd_under,
                  "open": sum(1 for q in pos if q["strategy"] == s),
                  "blocked": sum(v for (k, _), v in blocked.items() if k == s)}

    years = []
    prev_e, prev_r, prev_x = eq0, 0.0, 0.0
    for y in sorted({_yr(t) for t in ts}):
        k = np.flatnonzero([_yr(t) == y for t in ts])
        seg = ev[k]
        _, ddy, _ = _dd(np.concatenate([[prev_e], seg]))
        r_, x_ = curve[k[-1]][2], curve[k[-1]][3]
        years.append({"y": y, "pnl": float(seg[-1] - prev_e),
                      "ret": float(seg[-1] / prev_e - 1) if prev_e > 0 else None,
                      "rsi2": float(r_ - prev_r), "xsmom": float(x_ - prev_x),
                      "dd": ddy, "days": len(k)})
        prev_e, prev_r, prev_x = float(seg[-1]), r_, x_

    # gian mau duong von xuong ~1.500 diem cho trang nhe; giu ca diem cuoi
    step = max(1, len(curve) // 1500)
    pts = curve[::step]
    if pts[-1] is not curve[-1]:
        pts.append(curve[-1])

    return {
        "params": {k: v for k, v in p.items() if k not in ("start", "end")},
        "range": [int(ts[0]), int(ts[-1])], "secs": round(secs, 2),
        "data": {"symbols": len(D["syms"]), "first": int(D["T"][0]),
                 "last": int(D["T"][-1])},
        "dead": dead,
        "summary": {"start": eq0, "end": end, "pnl": end - eq0,
                    "ret": end / eq0 - 1, "cagr": cagr, "years": yrs,
                    "dd_usd": dd_usd, "dd_pc": dd_pc, "under": under,
                    "peak_gross": peak_g, "peak_margin": peak_mu,
                    "avg_open": nopen_sum / max(1, len(curve)),
                    "trades": len(trades),
                    "blocked": int(sum(blocked.values()))},
        "per": per, "years": years,
        "blocked": sorted(({"s": s, "why": w, "n": v}
                           for (s, w), v in blocked.items()),
                          key=lambda x: -x["n"]),
        "curve": [[c[0], round(c[1], 2), round(c[2], 2), round(c[3], 2)]
                  for c in pts],
        "trades": [{**t, "pnl": round(t["pnl"], 4), "fund": round(t["fund"], 4),
                    "usd": round(t["usd"], 2)}
                   for t in sorted(trades, key=lambda t: -t["z"])],
    }
