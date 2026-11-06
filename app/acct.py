"""Duong von THAT cua tai khoan tren san — hai duong cho bieu do «Đường vốn».

  von thuc   = so du vi + lai/lo chua chot (totalWalletBalance + totalUnrealizedProfit),
               chup moi 15 phut vao bang acct_snap. Truoc moc chup dau tien: lay
               cac moc von che do «live» ma luot chay hang ngay da ghi tu san.
  da ghi nhan = so du vi (von + lai/lo DA CHOT + phi + funding + nap/rut), dung lai
               nguoc tu so du hien tai va lich su thu nhap (/fapi/v1/income) — san
               giu 3 thang, nen duong nay co ngay ca cho quang truoc khi co anh chup.

Khac duong von cu (bang equity): bang do o che do giay la von theo SO cua bot
tinh tu START_EQUITY_USD, khong phai tien tren san.
"""
from __future__ import annotations

import threading
import time

from . import db
from .binance import Trader
from .config import CFG

_STABLE = {"USDT", "USDC", "BUSD", "FDUSD"}
_C: dict = {"at": 0.0, "v": None}
_L = threading.Lock()
_ERR: list = [None]


def snap() -> None:
    """Chup von tren san. Khong co khoa / san tu choi → bo qua, khong lam hong lich."""
    if not CFG.has_keys():
        return
    t = None
    try:
        t = Trader()
        a = t.account()
        with db.tx() as cx:
            cx.execute("INSERT OR REPLACE INTO acct_snap(ts, wallet, upnl) VALUES(?,?,?)",
                       (int(time.time() * 1000), float(a["totalWalletBalance"]),
                        float(a["totalUnrealizedProfit"])))
        _ERR[0] = None
    except Exception as e:
        if str(e) != _ERR[0]:           # moi 15 phut — chi ghi khi loi doi
            db.log("warn", f"chụp vốn trên sàn lỗi: {e}")
        _ERR[0] = str(e)
    finally:
        if t is not None:
            t.close()


_INC: dict = {"from": None, "upto": 0, "rows": {}}
WIN = 2 * 86_400_000


def _income(t: Trader, start: int, now: int) -> list:
    """Thu nhap tu start toi nay. Nho lai phan da tai: moi lan chi hoi tu moc
    da co (lui 1 phut cho dong cung mili-giay) toi nay, cua so 2 ngay."""
    if _INC["from"] is None or start < _INC["from"]:
        _INC.update(**{"from": start, "upto": start, "rows": {}})
    s = max(start, _INC["upto"] - 60_000)
    while s < now:
        e = min(s + WIN, now)
        while True:
            r = t.income(s, e)
            for x in r:
                _INC["rows"][(x.get("incomeType"), x.get("tranId"), x.get("asset"), x.get("symbol"))] = x
            n_s = max(int(x["time"]) for x in r) if r else s
            if len(r) < 1000 or n_s <= s:
                break
            s = n_s                         # trang day: hoi tiep tu dong moi nhat
        s = e + 1
    _INC["upto"] = now
    _INC["rows"] = {k: x for k, x in _INC["rows"].items() if int(x["time"]) >= start}
    return [x for x in _INC["rows"].values() if int(x["time"]) >= start]


def series() -> dict:
    """{"real": [{ts, value}], "booked": [{ts, value}], "transfers": [{ts, value}]}.

    Gom 60 giay: trang hoi 15 giay/lan, lich su thu nhap ton 30 trong so moi trang.
    """
    if not CFG.has_keys():
        return {"ok": False, "why": "chưa có khoá API"}
    with _L:
        if _C["v"] is not None and time.time() - _C["at"] < 60:
            return _C["v"]
        cx = db.connect()
        try:
            snaps = [dict(r) for r in cx.execute("SELECT ts, wallet, upnl FROM acct_snap ORDER BY ts")]
            # ts cua bang equity la mo nen ngay; von do luc chay (~00:05 hom sau)
            runs = [{"ts": int(r["ts"]) + 86_400_000, "value": float(r["value"])} for r in cx.execute(
                "SELECT ts, value FROM equity WHERE mode='live' ORDER BY ts")]
        finally:
            cx.close()
        t = None
        try:
            t = Trader()
            a = t.account()
            now = int(time.time() * 1000)
            w_now, u_now = float(a["totalWalletBalance"]), float(a["totalUnrealizedProfit"])
            # bat dau tu moc von dau tien cua bot; chua co thi 30 ngay; san giu 3 thang
            t0 = max(now - 89 * 86_400_000,
                     min([x["ts"] for x in snaps] + [x["ts"] for x in runs]) if snaps or runs
                     else now - 30 * 86_400_000)
            inc = [x for x in _income(t, t0, now) if x.get("asset") in _STABLE]
        except Exception as e:
            return {"ok": False, "why": str(e)[:200]}
        finally:
            if t is not None:
                t.close()
        # so du vi lui dan tu hien tai: truoc moi khoan thu nhap = sau no − khoan do
        inc.sort(key=lambda x: int(x["time"]))
        booked, w = [{"ts": now, "value": w_now}], w_now
        for x in reversed(inc):
            booked.append({"ts": int(x["time"]), "value": w})
            w -= float(x["income"])
        booked.append({"ts": t0, "value": w})
        booked.reverse()
        # mot moc moi gio (giu moc cuoi cua gio) — vai nghin dong phi/funding moi tuan
        hb: dict = {}
        for p in booked:
            hb[p["ts"] // 3_600_000] = p
        booked = sorted(hb.values(), key=lambda p: p["ts"])
        booked[-1] = {"ts": now, "value": w_now}

        # anh chup cu hon 2 ngay: giu mot moc moi gio (35.000 dong/nam → ~9.000)
        hs: dict = {}
        for x in snaps:
            hs[x["ts"] // 3_600_000 if x["ts"] < now - 2 * 86_400_000 else x["ts"]] = x
        snaps = sorted(hs.values(), key=lambda x: x["ts"])
        s0 = snaps[0]["ts"] if snaps else now
        real = ([r for r in runs if r["ts"] < s0]
                + [{"ts": int(s["ts"]), "value": float(s["wallet"]) + float(s["upnl"])} for s in snaps]
                + [{"ts": now, "value": w_now + u_now}])
        tr = [{"ts": int(x["time"]), "value": float(x["income"])}
              for x in inc if x.get("incomeType") == "TRANSFER"]
        v = {"ok": True, "real": real, "booked": booked, "transfers": tr, "ts": now}
        _C.update(at=time.time(), v=v)
        return v
