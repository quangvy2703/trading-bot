"""Cong voi Binance USDⓈ-M futures.

Tach doi co y: `pub` cho du lieu cong khai (khong khoa, luon tro ve endpoint
THAT vi testnet khong du lich su), `Trader` cho lenh co ky (can khoa).
"""
from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse

import httpx

from .config import CFG

DAY = 86_400_000


class PublicApi:
    def __init__(self) -> None:
        self._c = httpx.Client(base_url=CFG.public_rest, timeout=30.0,
                               headers={"User-Agent": "crypto-live/1"})

    def close(self) -> None:
        self._c.close()

    def _get(self, path: str, **params):
        for attempt in range(5):
            r = self._c.get(path, params=params)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        r.raise_for_status()

    def exchange_info(self) -> dict:
        return self._get("/fapi/v1/exchangeInfo")

    def klines(self, symbol: str, start_ms: int | None = None,
               limit: int = 1500) -> list:
        p = {"symbol": symbol, "interval": "1d", "limit": limit}
        if start_ms:
            p["startTime"] = start_ms
        return self._get("/fapi/v1/klines", **p)

    def klines_1h(self, symbol: str, start_ms: int, limit: int = 1500) -> list:
        """Nen 1H — chi de dung volume profile cho cat lo RSI(2), khong luu kho."""
        return self._get("/fapi/v1/klines", symbol=symbol, interval="1h",
                         startTime=int(start_ms), limit=int(limit))

    def prices(self) -> dict:
        """Gia khop gan nhat cho moi ma — dung lam gia vao/ra cua so giay."""
        return {x["symbol"]: float(x["price"])
                for x in self._get("/fapi/v1/ticker/price")}

    def funding(self, symbol: str, start_ms: int | None = None,
                limit: int = 1000) -> list:
        p = {"symbol": symbol, "limit": limit}
        if start_ms:
            p["startTime"] = start_ms
        return self._get("/fapi/v1/fundingRate", **p)


class Trader:
    """Chi duoc dung khi CFG.live_enabled_env VA cong tac trong UI deu bat.

    Lop nay khong tu kiem dieu kien do -- executor kiem truoc khi dung toi.
    Giu nguyen tac mot cho kiem duy nhat de khong co duong vong.
    """

    def __init__(self) -> None:
        if not CFG.has_keys():
            raise RuntimeError("thiếu BINANCE_API_KEY / BINANCE_API_SECRET")
        self._c = httpx.Client(base_url=CFG.rest, timeout=20.0,
                               headers={"X-MBX-APIKEY": CFG.api_key,
                                        "User-Agent": "crypto-live/1"})

    def close(self) -> None:
        self._c.close()

    def _sign(self, params: dict) -> str:
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        q = urllib.parse.urlencode(params, doseq=True)
        sig = hmac.new(CFG.api_secret.encode(), q.encode(),
                       hashlib.sha256).hexdigest()
        return f"{q}&signature={sig}"

    def _call(self, method: str, path: str, **params):
        q = self._sign(dict(params))
        r = self._c.request(method, f"{path}?{q}")
        if r.status_code >= 400:
            raise RuntimeError(f"{r.status_code} {r.text[:400]}")
        return r.json()

    def account(self) -> dict:
        return self._call("GET", "/fapi/v2/account")

    def positions(self) -> list:
        return self._call("GET", "/fapi/v2/positionRisk")

    def dual_side(self) -> bool:
        """True = tai khoan dang o che do HAI CHIEU (hedge).

        Ma nay dat lenh theo che do MOT CHIEU: khong gui positionSide va dung
        reduceOnly de dong. O che do hai chieu Binance tu choi het voi -4061.
        """
        r = self._call("GET", "/fapi/v1/positionSide/dual")
        return bool(r.get("dualSidePosition"))

    def balance(self) -> dict:
        """So du USDT: tong, kha dung, lai/lo chua chot."""
        a = self._call("GET", "/fapi/v2/account")
        for x in a.get("assets", []):
            if x.get("asset") == "USDT":
                return {"total": float(x.get("walletBalance", 0)),
                        "avail": float(x.get("availableBalance", 0)),
                        "upnl": float(x.get("unrealizedProfit", 0))}
        return {"total": 0.0, "avail": 0.0, "upnl": 0.0}

    def limit_order(self, symbol: str, side: str, qty: float,
                    price: float) -> dict:
        """Lenh gioi han GTC. Dung cho phep thu ket noi: dat gia that xa thi
        no khong the khop, va huy duoc ngay."""
        return self._call("POST", "/fapi/v1/order", symbol=symbol, side=side,
                          type="LIMIT", timeInForce="GTC", quantity=qty,
                          price=price)

    def book(self, symbol: str) -> tuple[float, float]:
        """Gia mua / ban tot nhat tren CHINH san dat lenh (testnet co so lenh rieng)."""
        r = self._c.get("/fapi/v1/ticker/bookTicker", params={"symbol": symbol})
        if r.status_code >= 400:
            raise RuntimeError(f"{r.status_code} {r.text[:400]}")
        x = r.json()
        return float(x["bidPrice"]), float(x["askPrice"])

    def post_only(self, symbol: str, side: str, qty: float, price: str,
                  reduce_only: bool = False) -> dict:
        """LIMIT GTX: chi duoc lam maker. Gia ma khop ngay thi san tra EXPIRED
        thay vi khop nhu taker — phi luon la phi maker."""
        p = {"symbol": symbol, "side": side, "type": "LIMIT", "timeInForce": "GTX",
             "quantity": qty, "price": price}
        if reduce_only:
            p["reduceOnly"] = "true"
        return self._call("POST", "/fapi/v1/order", **p)

    def order_status(self, symbol: str, order_id) -> dict:
        return self._call("GET", "/fapi/v1/order", symbol=symbol,
                          orderId=order_id)

    def cancel_order(self, symbol: str, order_id) -> dict:
        return self._call("DELETE", "/fapi/v1/order", symbol=symbol,
                          orderId=order_id)

    def margin_cross(self, symbol: str) -> None:
        """Chuyen ma sang ky quy CHEO. -4046 = da la cheo san, khong phai loi.

        San tu choi doi kieu (-4048) khi ma dang co vi the — luc do de lai cho
        `add_margin` xu ly."""
        try:
            self._call("POST", "/fapi/v1/marginType", symbol=symbol,
                       marginType="CROSSED")
        except RuntimeError as e:
            if '"code":-4046' not in str(e).replace(" ", ""):
                raise

    def set_leverage(self, symbol: str, lev: int) -> dict:
        return self._call("POST", "/fapi/v1/leverage", symbol=symbol,
                          leverage=int(lev))

    def add_margin(self, symbol: str, amount: float) -> dict:
        """Nap them ky quy cho vi the ISOLATED (type=1). Mot chieu: BOTH."""
        return self._call("POST", "/fapi/v1/positionMargin", symbol=symbol,
                          amount=f"{amount:.2f}", type=1)

    def market_order(self, symbol: str, side: str, qty: float,
                     reduce_only: bool = False) -> dict:
        p = {"symbol": symbol, "side": side, "type": "MARKET",
             "quantity": qty}
        if reduce_only:
            p["reduceOnly"] = "true"
        return self._call("POST", "/fapi/v1/order", **p)
