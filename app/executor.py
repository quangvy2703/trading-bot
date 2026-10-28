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


def _tick(price: float, f: dict, side: str) -> str:
    """Lam tron gia ve buoc gia, KHONG vuot sang phia doi dien: mua lam tron
    xuong, ban lam tron len. Tra chuoi de khong lot sai so dau phay dong."""
    tick = f.get("tick") or 0.01
    n = price / tick
    n = math.floor(n + 1e-9) if side == "BUY" else math.ceil(n - 1e-9)
    return f"{n * tick:.{int(f.get('pprec', 8))}f}"


def _fill_limit(trader: Trader, jobs: list) -> None:
    """Khop bang LIMIT GTX theo vong, sua `jobs` tai cho.

    Ca lo dat cung luc roi cho mot lan, khong tung lenh mot: 40 lenh × 5
    vong × 20 giay thi chi mat ~2 phut thay vi hon mot gio.

    Moi vong: dat o gia tot nhat CUNG PHIA (mua o bid, ban o ask) → cho →
    doc lai → huy phan chua khop → cong don. Lenh khong doc / huy duoc thi
    DUNG HAN voi ma do (co the van treo tren san) va bao loi to: dat them
    la co nguy co khop gap doi.
    """
    for _ in range(CFG.limit_rounds):
        live = [j for j in jobs if j["rem"] > 0 and not j["err"]]
        if not live:
            return
        for j in live:
            j["oid"] = None
            try:
                bid, ask = trader.book(j["sym"])
                px = _tick(bid if j["side"] == "BUY" else ask, j["f"], j["side"])
                r = trader.post_only(j["sym"], j["side"], j["rem"], px, j["close"])
                j["oid"] = r.get("orderId")
            except Exception as e:
                j["note"] = f"đặt limit lỗi: {str(e)[:200]}"
        time.sleep(CFG.limit_wait_s)
        for j in live:
            if j["oid"] is None:
                continue
            try:
                st = trader.order_status(j["sym"], j["oid"])
                if st.get("status") in ("NEW", "PARTIALLY_FILLED"):
                    try:
                        trader.cancel_order(j["sym"], j["oid"])
                    except Exception:
                        pass                    # vua khop het giua hai lan doc
                    st = trader.order_status(j["sym"], j["oid"])
                    if st.get("status") in ("NEW", "PARTIALLY_FILLED"):
                        raise RuntimeError("huỷ không được, lệnh vẫn treo")
                ex = float(st.get("executedQty") or 0)
                if ex > 0:
                    j["filled"] += ex
                    j["cost"] += ex * float(st.get("avgPrice") or 0)
                    j["maker"] += ex
                j["rem"] = round_qty(j["qty"] - j["filled"], j["f"])
            except Exception as e:
                j["err"] = True
                j["note"] = f"lệnh {j['oid']}: {str(e)[:200]}"
                db.log("error", f"{j['sym']} {j['side']} limit {j['oid']}: {e} — "
                                "KIỂM TAY trên Binance, lệnh có thể còn treo")
        jobs_left = [j for j in jobs if j["rem"] > 0 and not j["err"]]
        for j in jobs_left:
            # phan du qua nho de MO them thi thoi; DONG thi van phai dong het
            if not j["close"] and (j["rem"] < j["f"].get("minq", 0)
                                   or j["rem"] * j["ref"] < j["f"].get("minn", 5)):
                j["rem"] = 0.0


def _fill_market(trader: Trader, j: dict) -> None:
    r = trader.market_order(j["sym"], j["side"], j["rem"], reduce_only=j["close"])
    ex = float(r.get("executedQty") or 0) or j["rem"]
    j["filled"] += ex
    j["cost"] += ex * (float(r.get("avgPrice") or 0) or j["ref"])
    j["taker"] += ex
    j["rem"] = 0.0


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
        jobs = []
        for a in actions:
            px = prices.get(a["symbol"]) or 0.0
            side = ("BUY" if a["side"] > 0 else "SELL") if a["action"] == "OPEN" \
                else ("SELL" if a["side"] > 0 else "BUY")
            notional = float(a.get("notional")
                             or equity * abs(a.get("weight") or 0))
            qty = (notional / px) if px else 0.0
            # DONG phai tra dung khoi luong da mua, khong quy lai tu co USD theo
            # gia hien tai: gia tang thi ban thieu va de lai phan du tren san,
            # gia giam thi ban lo sang phan cua lop / so khac cung ma.
            if a["action"] == "CLOSE" and a.get("qty"):
                qty = float(a["qty"])
            j = {"a": a, "sym": a["symbol"], "side": side, "close": a["action"] == "CLOSE",
                 "ref": px, "notional": notional, "qty": qty, "rem": 0.0,
                 "filled": 0.0, "cost": 0.0, "maker": 0.0, "taker": 0.0,
                 "err": False, "note": "", "status": "paper", "f": {}}
            jobs.append(j)
            if trader is None:
                continue
            f = filt.get(a["symbol"], {})
            j["f"] = f
            j["qty"] = qty = round_qty(qty, f)
            if qty <= 0 or qty < f.get("minq", 0) or qty * px < f.get("minn", 5):
                j["status"], j["note"] = "bỏ qua", "khối lượng dưới mức tối thiểu của sàn"
                continue
            if not j["close"]:
                ensure_margin(trader, a["symbol"], held)
            j["rem"], j["status"] = qty, None

        work = [j for j in jobs if j["status"] is None]
        if work and CFG.order_mode == "limit":
            _fill_limit(trader, work)
        for j in work:
            if j["rem"] > 0 and not j["err"] and (
                    j["close"] or CFG.order_mode != "limit" or CFG.limit_fallback):
                try:
                    _fill_market(trader, j)
                except Exception as e:
                    j["err"] = True
                    j["note"] = f"lệnh thị trường lỗi: {str(e)[:200]}"
                    db.log("error", f"{j['sym']} {j['side']}: {e}")
            if j["filled"] <= 0:
                j["status"] = "lỗi" if j["err"] else "không khớp"
            elif j["close"] and j["rem"] > 0:
                # dong do dang: so noi bo giu vi the mo de luot sau dong tiep
                j["status"] = "lỗi"
                db.log("error", f"{j['sym']}: đóng mới khớp {j['filled']}/{j['qty']} "
                                "— phần còn lại vẫn trên sàn, KIỂM TAY")
            elif j["filled"] < j["qty"] - 1e-12:
                j["status"] = "khớp một phần"
            else:
                j["status"] = "khớp"

        for j in jobs:
            a, px, qty, notional = j["a"], j["ref"], j["qty"], j["notional"]
            resp = j["note"]
            if j["filled"] > 0:
                px = j["cost"] / j["filled"] if j["cost"] > 0 else px
                qty = j["filled"]
                if not j["close"]:
                    notional = qty * px        # so ghi theo phan THUC SU khop
                resp = json.dumps({"maker": j["maker"], "taker": j["taker"],
                                   "note": j["note"]}, ensure_ascii=False)
            with db.tx() as cx:
                cx.execute(
                    "INSERT INTO orders(run_id,ts,strategy,sleeve,symbol,action,"
                    "side,qty,notional,mode,status,px,resp) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run_id, int(time.time() * 1000), a["strategy"],
                     a.get("sleeve"), a["symbol"], a["action"], j["side"], qty,
                     notional, mode, j["status"], px, resp[:900]))
            done.append({**a, "px": px, "qty": qty, "status": j["status"],
                         **({"notional": notional} if j["filled"] > 0 else {})})
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
