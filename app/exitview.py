"""Chi so DONG LENH cua tung vi the dang mo — cho bang «Vị thế đang mở» ve bieu do.

Chi DOC (khong dat lenh, khong ghi so). Moi vi the tra cac luat se dong no tuy
chien luoc, kem phan tinh san de trinh duyet tinh lai moi tick tu gia danh dau:

  level  gia cham muc (dung an toan / cat lo / chot loi / Kase)   {level, dir: "le"|"ge", tf}
  u      lai theo R ≥ nguong (F08, P16 — lenh BAN dong luong)       {thr, q?, qmax?, t0?, t1?}
  z      nen 15m dang chay: side × ln(gia / close nen truoc) / sd ≥ K (windfall)   {c_prev, sd, thr}
  time   het ky (tai can bang so / het so ngay giu / C13 giu 1 ngay)                {t0, t1}
  rsi    RSI(2) Wilder voi gia hien tai lam close hom nay > nguong (RSI(2))        {c_last, au, ad, n, thr}

Gom 60 giay; nen 15m doi thi tinh lai windfall.
"""
from __future__ import annotations

import math
import threading
import time

import numpy as np

from . import db, executor, pp1tp, pp1x as PX, runner, settings, swing as SW
from .binance import DAY, PublicApi
from .config import CFG

M15 = 900_000
_C: dict = {"key": None, "at": 0.0, "v": None}
_L = threading.Lock()


def _daily(api: PublicApi, sym: str, start: int, now: int) -> dict | None:
    k = [x for x in api.klines(sym, int(start), 400) if int(x[6]) < now]
    if not k:
        return None
    return {"t": np.array([int(x[0]) for x in k], np.int64),
            "h": np.array([float(x[2]) for x in k]), "l": np.array([float(x[3]) for x in k]),
            "c": np.array([float(x[4]) for x in k])}


def _wf_state(api: PublicApi, sym: str, now: int, w: int) -> dict | None:
    """close nen 15m da dong gan nhat + sd w log-return 15m ket thuc o nen do."""
    last = now // M15 * M15                    # mo cua nen dang chay
    k = api.klines_iv(sym, "15m", last - (w + 1) * M15, w + 1)
    cl = {int(x[0]): float(x[4]) for x in k if int(x[6]) < now}
    grid = last - M15 * np.arange(w + 1, 0, -1, dtype=np.int64)
    c = np.array([cl.get(int(t), np.nan) for t in grid])
    if not np.isfinite(c[-1]):
        return None
    with np.errstate(all="ignore"):
        r = np.diff(np.log(c))
    ok = np.isfinite(r)
    if ok.sum() < 0.9 * w:
        return None
    sd = float(np.std(r[ok], ddof=1))
    return {"c_prev": float(c[-1]), "sd": sd, "bar": int(last)} if sd > 0 else None


def _rsi_state(c: np.ndarray, n: int) -> dict | None:
    """Trang thai Wilder sau nen da dong cuoi — trinh duyet cong them nen hom nay."""
    if len(c) <= n + 1:
        return None
    d = np.diff(c, prepend=c[0])
    up, dn = np.maximum(d, 0.0), np.maximum(-d, 0.0)
    au, ad = float(np.mean(up[1:n + 1])), float(np.mean(dn[1:n + 1]))
    for i in range(n + 1, len(c)):
        au = (au * (n - 1) + up[i]) / n
        ad = (ad * (n - 1) + dn[i]) / n
    return {"c_last": float(c[-1]), "au": au, "ad": ad, "n": n}


def compute(m: str) -> dict:
    book = runner.open_positions(m)
    now = int(time.time() * 1000)
    F = settings.pp1x()
    R, _ = settings.strat()
    api = PublicApi()
    try:
        syms = sorted({p["symbol"] for p in book})
        D: dict = {}
        WF: dict = {}
        # ngay UTC gan nhat da dong — cung ngay luot chot loi PP1 gio ke tiep dung
        d_q = (now // 3_600_000 * 3_600_000) // DAY * DAY - DAY
        shorts = sorted({p["symbol"] for p in book if p["strategy"] == "xsmom" and int(p["side"]) < 0})
        try:
            Q = pp1tp.spot_q(api, shorts, int(d_q)) if F.get("tp") and shorts else {}
        except Exception:
            Q = {}
        out = {}
        for p in book:
            s, side, st = p["symbol"], int(p["side"]), p["strategy"]
            rules = []
            n, r, e = p.get("notional"), p.get("r_usd"), p.get("entry_px")
            rf = float(r) / float(n) if n and r else None
            lv = executor.safety_level(p)
            if st == "xsmom":
                if lv:
                    rules.append({"k": "safety", "name": f"dừng {CFG.safety_r:g}R", "type": "level",
                                  "level": lv, "dir": "le" if side > 0 else "ge", "tf": "sàn"})
                if side > 0 and F.get("kase"):
                    if s not in D:
                        try:
                            D[s] = _daily(api, s, int(p["entry_ts"]) // DAY * DAY - 45 * DAY, now)
                        except Exception:
                            D[s] = None
                    d = D[s]
                    if d is not None:
                        a = int(np.searchsorted(d["t"], int(p["entry_ts"]) // DAY * DAY))
                        if a < len(d["t"]):
                            k_ = PX._kase_levels(d["h"], d["l"], d["c"], a, int(CFG.xsmom_kase_n),
                                                 float(CFG.xsmom_kase_k))[-1]
                            if np.isfinite(k_):
                                rules.append({"k": "kase", "name": "Kase", "type": "level", "level": float(k_),
                                              "dir": "le", "tf": "1D"})
                if side < 0 and F.get("tp") and rf:
                    q = Q.get(s)
                    rules.append({"k": "f08", "name": "F08", "type": "u", "thr": float(CFG.xsmom_tp_f08_m),
                                  "q": q, "qmax": 1 - float(CFG.xsmom_tp_f08_x), "tf": "1H"})
                    E = int(p["entry_ts"]) // DAY * DAY
                    h16 = int(CFG.xsmom_tp_p16_h)
                    t0, t1 = E + (h16 - 1) * DAY, E + h16 * DAY
                    if now <= t1:
                        rules.append({"k": "p16", "name": f"P16", "type": "u", "thr": float(CFG.xsmom_tp_p16_m),
                                      "t0": t0, "t1": t1, "tf": "1H"})
                wside = {"both": (1, -1), "long": (1,), "short": (-1,)}.get(CFG.xsmom_wf_side, (1, -1))
                if F.get("wf") and side in wside:
                    if s not in WF:
                        try:
                            WF[s] = _wf_state(api, s, now, int(CFG.xsmom_wf_w))
                        except Exception:
                            WF[s] = None
                    if WF[s]:
                        rules.append({"k": "wf", "name": "windfall", "type": "z", "thr": float(CFG.xsmom_wf_k),
                                      **WF[s], "tf": "15m"})
                t1 = runner.planned_exit(p)
                if t1:
                    hold = settings.strat()[1]["hold"]
                    rules.append({"k": "reb", "name": "tái cân bằng", "type": "time",
                                  "t0": max(int(p["entry_ts"]), t1 - hold * DAY), "t1": t1})
            elif st in ("tsvw", "dsrm", "imd"):
                if p.get("stop"):
                    rules.append({"k": "stop", "name": "cắt lỗ", "type": "level", "level": float(p["stop"]),
                                  "dir": "le" if side > 0 else "ge", "tf": "sàn"})
                if p.get("tp"):
                    rules.append({"k": "tp", "name": "chốt lời", "type": "level", "level": float(p["tp"]),
                                  "dir": "ge" if side > 0 else "le", "tf": "15m"})
                hd = (SW.PARAMS.get(st) or {}).get("hold")
                if hd:
                    E = int(p["entry_ts"]) // DAY * DAY
                    rules.append({"k": "hold", "name": f"giữ {hd} ngày", "type": "time",
                                  "t0": int(p["entry_ts"]), "t1": E + int(hd) * DAY})
            elif st == "rsi2":
                if p.get("stop"):
                    rules.append({"k": "stop", "name": "cắt lỗ", "type": "level", "level": float(p["stop"]),
                                  "dir": "le", "tf": "1D"})
                if s not in D:
                    try:
                        D[s] = _daily(api, s, now - 120 * DAY, now)
                    except Exception:
                        D[s] = None
                rs = _rsi_state(D[s]["c"], 2) if D.get(s) is not None else None
                if rs:
                    rules.append({"k": "rsi", "name": "RSI(2)", "type": "rsi", "thr": float(R["rsi_out"]),
                                  **rs, "tf": "1D"})
            else:
                if lv:
                    rules.append({"k": "stop", "name": "cắt lỗ", "type": "level", "level": lv,
                                  "dir": "le" if side > 0 else "ge", "tf": "sàn"})
                if st == "c13":
                    t1 = runner.planned_exit(p) or ((int(p["entry_ts"]) // DAY + 1) * DAY
                                                    + _run_offset())
                    rules.append({"k": "time", "name": "giữ 1 ngày", "type": "time",
                                  "t0": int(p["entry_ts"]), "t1": t1})
            out[str(p["id"])] = {"symbol": s, "side": side, "strategy": st, "sleeve": p.get("sleeve"),
                                 "entry_px": e, "rf": rf, "rules": rules}
        try:                                   # gia du phong khi trinh duyet mat luong gia
            pr = api.prices()
            px = {k: float(pr[k]) for k in syms if pr.get(k)}
        except Exception:
            px = {}
        return {"ok": True, "ts": now, "pos": out, "px": px}
    finally:
        api.close()


def _run_offset() -> int:
    hh, _, mm = CFG.run_at_utc.partition(":")
    return (int(hh) * 60 + int(mm or 0)) * 60_000


def get(m: str) -> dict:
    now = time.time()
    with _L:
        key = (m, tuple(sorted(p["id"] for p in runner.open_positions(m))), int(now * 1000) // M15)
        if _C["v"] is not None and _C["key"] == key and now - _C["at"] < 60:
            return _C["v"]
        try:
            v = compute(m)
        except Exception as e:
            return {"ok": False, "why": str(e)[:200]}
        _C.update(key=key, at=now, v=v)
        return v
