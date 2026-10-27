"""Dat lenh: so giay luon chay, so that chi chay khi CA HAI khoa deu mo.

Khoa 1 (tang ma)  : bien moi truong LIVE_TRADING_ENABLED=1
Khoa 2 (nguoi dung): cong tac `live_armed` trong CSDL, bat tu UI kem xac nhan

Thieu mot trong hai thi `place_live` khong bao gio duoc goi. Co y de mot cu
bam nham trong trinh duyet khong the dong vao tien that.
"""
from __future__ import annotations

import json
import math
import time

from . import db, settings
from .binance import Trader
from .config import CFG


def live_armed() -> bool:
    return bool(db.kv_get("live_armed", False))


def live_ready() -> tuple[bool, str]:
    """Du dieu kien dat lenh that chua, va neu chua thi vi sao."""
    if not CFG.live_enabled_env:
        return False, "LIVE_TRADING_ENABLED=0 trong môi trường container"
    if not CFG.has_keys():
        return False, "thiếu BINANCE_API_KEY / BINANCE_API_SECRET"
    if not live_armed():
        return False, "công tắc chạy thật đang TẮT"
    return True, ""


def round_qty(q: float, f: dict) -> float:
    step = f.get("step") or 0.001
    q = math.floor(q / step) * step
    return round(q, max(0, int(round(-math.log10(step)))) if step < 1 else 0)


def plan(target: list, actual: list) -> list:
    """So mục tieu vs so hien tai -> danh sach viec can lam.

    Khoa dong nhat cua mot vi the la (chien luoc, so, ma, chieu): cung mot ma
    co the vua nam o chan mua cua so nay vua o chan ban cua so kia, va do la
    hai vi the KHAC NHAU, khong duoc bu tru o day.
    """
    key = lambda p: (p["strategy"], p.get("sleeve"), p["symbol"], p["side"])  # noqa: E731
    tgt = {key(p): p for p in target}
    act = {key(p): p for p in actual}
    out = []
    for k, p in act.items():
        if k not in tgt:
            out.append({"action": "CLOSE", **p})
    for k, p in tgt.items():
        if k not in act:
            out.append({"action": "OPEN", **p})
    out.sort(key=lambda x: (x["action"] != "CLOSE", x["symbol"]))
    return out


def one_way(actions: list, actual: list) -> tuple[list, list]:
    """Chan mo vi the NGUOC CHIEU voi vi the dang co tren cung mot ma.

    San chay che do mot chieu: moi ma chi co MOT vi the rong. Hai so lech
    ngay cua dong luong co the vua mua vua ban cung mot ma — trong so noi bo
    do la hai vi the, tren san chung bu tru nhau. Hau qua that su nam o luc
    dong: reduceOnly tren mot vi the da bi bu tru bang 0 se bi san tu choi,
    va vi the do ket lai trong so mai mai.

    Cung chieu thi khong chan: san gop khoi luong lai, va lenh dong kem
    reduceOnly co ghi ro khoi luong nen van tru dung phan cua tung so.

    Chi goi o che do that. So giay van chay dung nhu backtest.
    """
    closing = {(a["strategy"], a.get("sleeve"), a["symbol"], a["side"])
               for a in actions if a["action"] == "CLOSE"}
    side_of: dict = {}
    for p in actual:
        if (p["strategy"], p.get("sleeve"), p["symbol"], p["side"]) in closing:
            continue                            # luot nay dong, khong tinh nua
        side_of.setdefault(p["symbol"], p["side"])
    ok, blocked = [], []
    for a in actions:
        if a["action"] == "CLOSE":
            ok.append(a)                        # dong khong bao gio bi chan
            continue
        held = side_of.get(a["symbol"])
        if held is not None and held != a["side"]:
            blocked.append({**a, "why": "đã có vị thế ngược chiều trên mã này "
                                        "(sàn chạy chế độ một chiều)"})
            continue
        side_of.setdefault(a["symbol"], a["side"])
        ok.append(a)
    return ok, blocked


def apply_caps(actions: list, equity: float, prices: dict,
               n_held: int = 0) -> tuple[list, list]:
    """Ap tran rui ro TRUOC khi gui bat ky lenh nao. Tra (duoc phep, bi chan).

    Co lenh KHONG con tinh tu von: no bang r_usd / R, da tinh san o so muc
    tieu. Von chi con quyet dinh mo duoc bao nhieu lenh cung luc — do la
    `max_open` va `gross`.
    """
    R = settings.risk()
    ok, blocked = [], []
    gross = 0.0
    n_open = 0
    live = n_held - sum(1 for a in actions if a["action"] == "CLOSE")
    for a in actions:
        if a["action"] == "CLOSE":
            ok.append(a)                       # dong vi the khong bao gio bi chan
            continue
        px = prices.get(a["symbol"])
        if not px:
            blocked.append({**a, "why": "không có giá"})
            continue
        notional = float(a.get("notional") or equity * abs(a.get("weight") or 0))
        if live + n_open >= R["max_open"]:
            blocked.append({**a, "why": f"đã đủ {R['max_open']} lệnh mở cùng lúc"})
            continue
        if notional > R["order"]:
            blocked.append({**a, "why": f"vượt trần lệnh {R['order']:.0f} USD"})
            continue
        if gross + notional > R["gross"]:
            blocked.append({**a, "why": f"vượt trần tổng {R['gross']:.0f} USD"})
            continue
        if n_open >= R["orders"]:
            blocked.append({**a, "why": "vượt trần số lệnh mỗi lượt"})
            continue
        gross += notional
        n_open += 1
        ok.append({**a, "notional": notional})
    return ok, blocked


def ensure_margin(trader: Trader, symbol: str, held: dict) -> None:
    """Truoc khi MO: dua ma ve ky quy cheo + don bay chuan.

    Thiet lap san co tren tai khoan co the la bat cu gi (da gap SOLUSDT
    isolated 40x: 0,97 USD ky quy, thanh ly khi gia di nguoc 1,9% — chua toi
    mot ngay bien dong). Loi o day KHONG chan lenh: lenh van vao, va
    `fix_isolated` chay sau cung luot se nap ky quy neu no ket o isolated.
    """
    p = held.get(symbol)
    if not (p and float(p.get("positionAmt") or 0) != 0
            and p.get("marginType") == "isolated"):
        try:
            trader.margin_cross(symbol)
        except Exception as e:
            db.log("warn", f"{symbol}: không chuyển được sang ký quỹ chéo: {e}")
    try:
        if int(float((p or {}).get("leverage") or 0)) != CFG.leverage:
            trader.set_leverage(symbol, CFG.leverage)
    except Exception as e:
        db.log("warn", f"{symbol}: không đặt được đòn bẩy {CFG.leverage}x: {e}")


def fix_isolated(trader: Trader) -> list:
    """Vi the ISOLATED dang mo: nap them cho toi khi ky quy >= |co lenh|/don bay.

    San khong cho doi isolated -> cheo khi ma con vi the (-4048), nen day la
    cach duy nhat lam no an toan ma khong phai dong lenh. Khi vi the dong,
    lan MO ke tiep `ensure_margin` se dua ma ve cheo.
    """
    out = []
    avail = trader.balance()["avail"]
    for p in trader.positions():
        if float(p.get("positionAmt") or 0) == 0 or p.get("marginType") != "isolated":
            continue
        sym = p["symbol"]
        need = abs(float(p["notional"])) / CFG.leverage
        add = need - float(p.get("isolatedWallet") or 0)
        if add < 0.01:
            continue
        add = min(add, avail * 0.9)
        if add < 0.01:
            db.log("error", f"{sym} isolated thiếu ký quỹ nhưng ví không còn "
                            f"số dư khả dụng — giá thanh lý {p.get('liquidationPrice')}")
            continue
        try:
            trader.add_margin(sym, add)
            avail -= add
            msg = (f"{sym} isolated {p.get('leverage')}x: nạp thêm {add:.2f} USDT "
                   f"ký quỹ (giá thanh lý trước đó {float(p['liquidationPrice']):g})")
            db.log("warn", msg)
            out.append(msg)
        except Exception as e:
            db.log("error", f"{sym}: nạp ký quỹ isolated lỗi: {e}")
    return out


def execute(run_id: int, actions: list, equity: float, prices: dict,
            filt: dict, mode: str) -> list:
    """mode = 'paper' | 'live'. Tra ve danh sach lenh da ghi."""
    trader = None
    if mode == "live":
        ready, why = live_ready()
        if not ready:                          # chot chan cuoi cung
            raise RuntimeError(f"không đủ điều kiện chạy thật: {why}")
        trader = Trader()
    done = []
    try:
        held = ({p["symbol"]: p for p in trader.positions()}
                if trader is not None else {})
        for a in actions:
            px = prices.get(a["symbol"]) or 0.0
            side = ("BUY" if a["side"] > 0 else "SELL") if a["action"] == "OPEN" \
                else ("SELL" if a["side"] > 0 else "BUY")
            notional = float(a.get("notional")
                             or equity * abs(a.get("weight") or 0))
            qty = (notional / px) if px else 0.0
            status, resp = "paper", ""
            if trader is not None:
                f = filt.get(a["symbol"], {})
                qty = round_qty(qty, f)
                if qty <= 0 or qty < f.get("minq", 0) or qty * px < f.get("minn", 5):
                    status, resp = "bỏ qua", "khối lượng dưới mức tối thiểu của sàn"
                else:
                    if a["action"] == "OPEN":
                        ensure_margin(trader, a["symbol"], held)
                    try:
                        r = trader.market_order(
                            a["symbol"], side, qty,
                            reduce_only=(a["action"] == "CLOSE"))
                        status, resp = "khớp", json.dumps(r)[:900]
                        if r.get("avgPrice"):
                            px = float(r["avgPrice"]) or px
                    except Exception as e:
                        status, resp = "lỗi", str(e)[:900]
                        db.log("error", f"{a['symbol']} {side}: {e}")
            with db.tx() as cx:
                cx.execute(
                    "INSERT INTO orders(run_id,ts,strategy,sleeve,symbol,action,"
                    "side,qty,notional,mode,status,px,resp) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run_id, int(time.time() * 1000), a["strategy"],
                     a.get("sleeve"), a["symbol"], a["action"], side, qty,
                     notional, mode, status, px, resp))
            done.append({**a, "px": px, "qty": qty, "status": status})
        if trader is not None:
            # Lenh da khop roi: loi o day tuyet doi khong duoc lam mat `done`,
            # neu khong so noi bo se lech san.
            try:
                fix_isolated(trader)
            except Exception as e:
                db.log("error", f"rà ký quỹ isolated lỗi: {e}")
    finally:
        if trader is not None:
            trader.close()
    return done
