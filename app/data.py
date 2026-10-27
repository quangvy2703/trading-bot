"""Kho nen 1D + funding: gieo mam tu cache nghien cuu, roi cap nhat tang phan."""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from . import db
from .binance import DAY, PublicApi
from .config import CFG


def seed_from_npz(path: str | None = None) -> int:
    """Nap nhanh tu reports/.cache/uni1d neu o dia duoc mount.

    Khong bat buoc: thieu thi lan chay dau tu tai tu Binance, chi lau hon.
    """
    d = Path(path or CFG.seed_dir)
    if not d.is_dir():
        return 0
    n = 0
    # Mot giao dich MOI TEP, khong gom het vao mot giao dich: 1.500 tep trong
    # mot tx se giu khoa ghi hang phut va treo ca ung dung.
    for f in sorted(d.glob("*.npz")):
        sym = f.stem
        try:
            z = np.load(f)
        except Exception:
            continue
        with db.tx() as cx:
            if sym.endswith("-fund"):
                a = z["f"] if "f" in z else None
                if a is not None and len(a):
                    cx.executemany(
                        "INSERT OR IGNORE INTO funding(symbol,ts,rate)"
                        " VALUES(?,?,?)",
                        [(sym[:-5], int(t), float(r)) for t, r in a])
                    n += 1
            else:
                a = z["k"] if "k" in z else None
                if a is not None and len(a):
                    cx.executemany(
                        "INSERT OR IGNORE INTO bars(symbol,ts,o,h,l,c,v) "
                        "VALUES(?,?,?,?,?,?,?)",
                        [(sym, int(r[0]), *map(float, r[1:6])) for r in a])
                    n += 1
    db.log("info", f"gieo mầm {n} tệp từ {d}")
    return n


def known_symbols() -> list[str]:
    cx = db.connect()
    try:
        return [r[0] for r in cx.execute(
            "SELECT DISTINCT symbol FROM bars ORDER BY symbol")]
    finally:
        cx.close()


def live_symbols(api: PublicApi) -> list[str]:
    info = api.exchange_info()
    return sorted(s["symbol"] for s in info["symbols"]
                  if s.get("contractType") == "PERPETUAL"
                  and s.get("quoteAsset") == "USDT"
                  and s.get("status") == "TRADING")


def filters(api: PublicApi) -> dict:
    """stepSize / minQty / minNotional de lam tron khoi luong lenh."""
    out = {}
    for s in api.exchange_info()["symbols"]:
        f = {x["filterType"]: x for x in s.get("filters", [])}
        out[s["symbol"]] = {
            "step": float(f.get("LOT_SIZE", {}).get("stepSize", "0.001")),
            "minq": float(f.get("LOT_SIZE", {}).get("minQty", "0")),
            "minn": float(f.get("MIN_NOTIONAL", {}).get("notional", "5")),
            "prec": int(s.get("quantityPrecision", 3)),
            "tick": float(f.get("PRICE_FILTER", {}).get("tickSize", "0.01")),
            "pprec": int(s.get("pricePrecision", 2))}
    return out


def refresh(api: PublicApi, symbols: list[str], log_every: int = 50) -> int:
    """Tai bo sung tu nen cuoi cung da co. Khong tai lai thu da co."""
    cx = db.connect()
    last = dict(cx.execute("SELECT symbol, MAX(ts) FROM bars GROUP BY symbol"))
    lastf = dict(cx.execute("SELECT symbol, MAX(ts) FROM funding GROUP BY symbol"))
    cx.close()
    n = 0
    for i, sym in enumerate(symbols):
        try:
            st = last.get(sym)
            # Da co lich su thi chi can vai nen moi -> limit nho, trong so 2
            # thay vi 10. Voi 600 ma moi luot, khac biet nay quyet dinh viec
            # co dung tran 2.400 trong so/phut hay khong.
            ks = api.klines(sym, start_ms=(st + DAY) if st else None,
                            limit=200 if st else 1500)
            rows = [(sym, int(k[0]), float(k[1]), float(k[2]), float(k[3]),
                     float(k[4]), float(k[5])) for k in ks
                    if int(k[6]) < time.time() * 1000]   # chi nen DA DONG
            stf = lastf.get(sym)
            fs = api.funding(sym, start_ms=(stf + 1) if stf else None)
            frows = [(sym, int(x["fundingTime"]), float(x["fundingRate"]))
                     for x in fs]
            if rows or frows:
                with db.tx() as cx2:
                    if rows:
                        cx2.executemany(
                            "INSERT OR REPLACE INTO bars(symbol,ts,o,h,l,c,v)"
                            " VALUES(?,?,?,?,?,?,?)", rows)
                    if frows:
                        cx2.executemany(
                            "INSERT OR IGNORE INTO funding(symbol,ts,rate)"
                            " VALUES(?,?,?)", frows)
                n += len(rows)
        except Exception as e:                      # mot ma hong khong duoc
            db.log("warn", f"tải {sym} lỗi: {e}")   # lam hong ca luot chay
        if log_every and (i + 1) % log_every == 0:
            db.log("info", f"tải {i + 1}/{len(symbols)} mã")
            time.sleep(1.0)                      # nhuong tran trong so cua san
    return n


def load_all(min_bars: int) -> dict:
    """Doc toan bo kho nen ra mang numpy, mot lan moi luot chay."""
    cx = db.connect()
    try:
        rows = cx.execute(
            "SELECT symbol, ts, o, h, l, c, v FROM bars ORDER BY symbol, ts"
        ).fetchall()
    finally:
        cx.close()
    out, cur, buf = {}, None, []

    def flush():
        if cur and len(buf) >= min_bars:
            a = np.array(buf, dtype=float)
            out[cur] = {"t": a[:, 0].astype(np.int64), "o": a[:, 1],
                        "h": a[:, 2], "l": a[:, 3], "c": a[:, 4], "v": a[:, 5]}
    for r in rows:
        if r["symbol"] != cur:
            flush()
            cur, buf = r["symbol"], []
        buf.append([r["ts"], r["o"], r["h"], r["l"], r["c"], r["v"]])
    flush()
    return out


def is_crypto(b: dict) -> bool:
    """Loai perp co phieu / kim loai: chung nghi cuoi tuan, crypto chay 24/7."""
    dow = ((b["t"] // DAY) + 4) % 7
    we = np.isin(dow, [5, 6])
    dv = b["c"] * b["v"]
    wd = np.median(dv[~we]) if (~we).any() else 0.0
    return bool(wd > 0 and we.any() and np.median(dv[we]) / wd > 0.45)
