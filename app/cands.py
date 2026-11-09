"""Ung cu vien moi gio: luot ngay TOI se chon ma nao, neu nen ngay dong o gia bay gio.

Luot ngay chi tinh tren nen 1D DA DONG. Bang nay tinh truoc: lay nen ngay dang
chay (va nen da dong ma kho chua tai) cua cac ma top thanh khoan tu Binance,
gan vao kho NHU THE ngay da dong o gia hien tai, roi chay DUNG cac ham tin hieu
cua luot ngay (strategies / swing). Khong dat lenh, khong ghi nen vao kho.

Khac luot that o cho: chua tru cho trong / ma dang giu / tran rui ro, khong ap
cac luat phu PP1 (funding, BSADF, Kase), stop RSI(2) la 6×ATR (khong dung HVN).
Hang thanh khoan dung nen ngay chua du khoi luong — sat cuoi ngay moi sat that.

Chi bot chinh tinh (vai chuc loi goi Binance moi gio); bot cua user doc ket
qua tu kho admin (CFG.market_db) va tu danh dau ma ho dang giu.
"""
from __future__ import annotations

import time

import numpy as np

from . import data, db, settings
from . import delist as DL
from . import strategies as ST
from . import swing as SW
from .binance import DAY, PublicApi
from .config import CFG

KEY = "cands"
ORDER = ("xsmom", "rsi2", "tsvw", "dsrm", "imd")


def _next_run(now_ms: int) -> int:
    hh, _, mm = CFG.run_at_utc.partition(":")
    t = now_ms // DAY * DAY + (int(hh) * 60 + int(mm or 0)) * 60_000
    return t if t > now_ms else t + DAY


def compute() -> dict:
    R, X = settings.strat()
    A, K = settings.alloc(), settings.risk()
    now = int(time.time() * 1000)
    nr = _next_run(now)
    day = nr // DAY * DAY - DAY                 # nen ngay ma luot toi se dung
    bars = {s: b for s, b in data.load_all(R["min_bars"]).items() if data.is_crypto(b)}
    if not bars:
        raise RuntimeError("kho nến rỗng")
    # Hang so bo tren nen da dong cuoi cung de chon ma can tai — du rong (+20)
    # vi hang tren nen tam tinh co the xe dich.
    last = int(max(b["t"][-1] for b in bars.values()))
    dv = sorted(((float(np.median((b["c"] * b["v"])[-30:])), s)
                 for s, b in bars.items() if b["t"][-1] == last), reverse=True)
    topn = max(R["topn"], X["topn"], *(SW.PARAMS[s]["topn"] for s in ("tsvw", "dsrm", "imd")))
    want = [s for _, s in dv[:topn + 20]]
    api, got = PublicApi(), 0
    try:
        for sym in want:
            b = bars[sym]
            if int(b["t"][-1]) >= day:              # kho da co nen do (da dong)
                bars[sym] = {k: v[:int(np.searchsorted(b["t"], day)) + 1] for k, v in b.items()}
                continue
            try:
                ks = api.klines(sym, start_ms=int(b["t"][-1]) + DAY, limit=5)
            except Exception as e:
                db.log("warn", f"ứng cử viên: tải nến {sym} lỗi: {e}")
                continue
            ks = [k for k in ks if int(k[0]) <= day]
            if not ks or int(ks[-1][0]) != day:
                continue
            a = np.array([[float(x) for x in k[:6]] for k in ks])
            bars[sym] = {"t": np.concatenate([b["t"], a[:, 0].astype(np.int64)]),
                         **{c: np.concatenate([b[c], a[:, i]])
                            for i, c in enumerate(("o", "h", "l", "c", "v"), 1)}}
            got += 1
            time.sleep(0.05)
    finally:
        api.close()
    P = ST.prep({s: bars[s] for s in want if s in bars and bars[s]["t"][-1] == day})
    rank = ST.ranks_on(P, day)
    try:
        nobuy = DL.banned(DL.notices(), now, K["ban_days"])
    except Exception:
        nobuy = {}
    rows, meth = [], {}

    def add(s, f):
        try:
            out = f()
            rows.extend({"strategy": s, **x} for x in out)
            meth[s] = {"on": float(A.get(s, 0)) > 0, "n": len(out)}
        except Exception as e:
            meth[s] = {"on": float(A.get(s, 0)) > 0, "n": 0, "err": str(e)[:200]}

    def xs():
        out = ST.xsmom_target(P, rank, day, nobuy) or []
        return [{"symbol": x["symbol"], "side": x["side"], "rank": rank.get(x["symbol"]),
                 "close": float(P[x["symbol"]]["c"][-1]),
                 "rf": float(x["vol"]) * float(X["hold"]) ** 0.5,
                 "why": f"điểm {x['score']:+.2f}"} for x in out]

    def rs():
        out = []
        for x in ST.rsi2_signals(P, rank, day, {}, nobuy):
            st = ST.rsi2_stop(x["close"], x["atr"])
            out.append({"symbol": x["symbol"], "side": 1, "rank": x["rank"], "close": x["close"],
                        "stop": st, "rf": (x["close"] - st) / x["close"],
                        "why": f"RSI(2) {x['rsi']:.1f}"})
        return out

    def sw(s):
        return [{"symbol": x["symbol"], "side": x["side"], "rank": x["rank"], "close": x["close"],
                 "stop": x["stop"], "rf": x["rf"], "why": f"chốt {SW.PARAMS[s]['tp_r']:g}R"}
                for x in SW.signals_today(s, P, rank, day, set(), nobuy)]

    add("xsmom", xs)
    add("rsi2", rs)
    for s in ("tsvw", "dsrm", "imd"):
        add(s, lambda s=s: sw(s))
    e = db.kv_get("xsmom_epoch")
    return {"ts": now, "day": day, "provisional": day + DAY > now, "next_run": nr,
            "sleeve": ST.xsmom_sleeve_of(day, int(e)) if e is not None else None,
            "fetched": got, "universe": len(rank), "methods": meth, "rows": rows}


def run_once() -> None:
    """Lich moi gio (bot chinh). Loi thi giu ban cu, ghi kem loi."""
    if CFG.market_db:
        return
    try:
        db.kv_set(KEY, compute())
    except Exception as e:
        old = db.kv_get(KEY) or {}
        db.kv_set(KEY, {**old, "err": str(e)[:300], "err_ts": int(time.time() * 1000)})
        db.log("warn", f"ứng cử viên: tính lỗi: {e}")


def get(open_pos: list) -> dict:
    """Ban moi nhat + danh dau ma TAI KHOAN NAY dang giu (cung phuong phap, chieu)."""
    v = (db.kv_get_at(CFG.market_db, KEY) if CFG.market_db else db.kv_get(KEY)) or {}
    held = {(p["strategy"], p["symbol"], p["side"]) for p in open_pos}
    held_sym = {(p["strategy"], p["symbol"]) for p in open_pos}
    for r in v.get("rows", []):
        r["held"] = ((r["strategy"], r["symbol"], r["side"]) in held) or \
            ("other" if (r["strategy"], r["symbol"]) in held_sym else False)
    v["order"] = ORDER
    v["alloc"] = settings.alloc()
    return v
