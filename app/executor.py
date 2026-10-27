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
               n_held: int = 0, held_gross: float = 0.0) -> tuple[list, list]:
    """Ap tran rui ro TRUOC khi gui bat ky lenh nao. Tra (duoc phep, bi chan).

    Co lenh KHONG con tinh tu von: no bang r_usd / R, da tinh san o so muc
    tieu. Von chi con quyet dinh mo duoc bao nhieu lenh cung luc — do la
    `max_open`, `gross` (phan mo them trong luot) va `gross_x` (TONG phoi
    nhiem ke ca vi the dang giu, `held_gross`, tru phan luot nay dong).
    """
    R = settings.risk()
    ok, blocked = [], []
    gross = 0.0
    n_open = 0
    live = n_held - sum(1 for a in actions if a["action"] == "CLOSE")
    held = held_gross - sum(float(a.get("notional") or 0.0)
                            for a in actions if a["action"] == "CLOSE")
    tot_cap = R["gross_x"] * equity
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
        if held + gross + notional > tot_cap:
            blocked.append({**a, "why": f"vượt trần tổng phơi nhiễm "
                                        f"{R['gross_x']:g}× vốn = {tot_cap:.0f} USD"})
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


def safety_level(p: dict) -> float | None:
    """Gia kich hoat dung an toan cua MOT vi the trong so.

    RSI(2): dung muc cat lo cua no. Dong luong: SAFETY_R lan R tinh tu gia
    vao, voi R = r_usd / co lenh (chinh la sigma x sqrt(so ngay giu)).
    """
    if p["strategy"] == "rsi2" and p.get("stop"):
        return float(p["stop"])
    n, r, e = p.get("notional"), p.get("r_usd"), p.get("entry_px")
    if not (n and r and e):
        return None
    d = min(CFG.safety_r * float(r) / float(n), 0.95)
    return float(e) * (1 - p["side"] * d)


def sync_safety(trader: Trader, book: list, filt: dict) -> dict:
    """Moi ma dang co vi the (va co trong so) giu DUNG MOT lenh dung an toan.

    San mot chieu: moi ma mot vi the rong, nen dung closePosition cho ca ma,
    o muc XA nhat trong cac vi the so cung chieu (nhieu lop / nhieu so). Lenh
    cu sai muc thi huy dat lai; ma het vi the thi huy lenh thua. Ma «ngoài
    sổ» KHONG dong toi — app khong biet no la gi.
    """
    ex = {p["symbol"]: float(p["positionAmt"]) for p in trader.positions()
          if float(p.get("positionAmt") or 0) != 0}
    mine: dict = {}
    for o in trader.open_algo_orders():
        if str(o.get("clientAlgoId", "")).startswith("sl-"):
            mine.setdefault(o["symbol"], []).append(o)
    out = {}
    for sym, amt in ex.items():
        side = 1 if amt > 0 else -1
        lv = [x for x in (safety_level(p) for p in book
                          if p["symbol"] == sym and p["side"] == side) if x]
        f = filt.get(sym)
        if not lv or not f:
            continue
        tick = f["tick"] or 0.0001
        # Lam tron RA XA (an toan hon), khong bao gio vao gan gia.
        trig = (math.floor(min(lv) / tick) * tick if side > 0
                else math.ceil(max(lv) / tick) * tick)
        trig_s = f"{trig:.{f['pprec']}f}"
        osd = "SELL" if side > 0 else "BUY"
        keep = None
        for o in mine.pop(sym, []):
            if (keep is None and o.get("side") == osd
                    and abs(float(o.get("triggerPrice") or 0) - trig) < tick / 2):
                keep = o
                continue
            try:
                trader.cancel_algo(o["algoId"])
            except Exception as e:
                db.log("warn", f"{sym}: huỷ dừng an toàn cũ lỗi: {e}")
        if keep is None:
            try:
                keep = trader.stop_close(sym, osd, trig_s,
                                         f"sl-{sym}-{int(time.time())}"[:36])
                db.log("info", f"{sym}: đặt dừng an toàn trên sàn {osd} "
                               f"khi giá đánh dấu {'≤' if side > 0 else '≥'} {trig_s}")
            except Exception as e:
                db.log("error", f"{sym}: KHÔNG đặt được dừng an toàn {trig_s}: {e}")
                continue
        out[sym] = {"algoId": keep.get("algoId"), "trigger": trig, "side": side}
    for sym, os_ in mine.items():              # ma da het vi the
        for o in os_:
            try:
                trader.cancel_algo(o["algoId"])
            except Exception as e:
                db.log("warn", f"{sym}: huỷ dừng an toàn thừa lỗi: {e}")
    db.kv_set("safety", out)
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
            # DONG phai tra dung khoi luong da mua, khong quy lai tu co USD theo
            # gia hien tai: gia tang thi ban thieu va de lai phan du tren san,
            # gia giam thi ban lo sang phan cua lop / so khac cung ma.
            if a["action"] == "CLOSE" and a.get("qty"):
                qty = float(a["qty"])
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
