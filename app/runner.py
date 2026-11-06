"""Mot luot chay hang ngay, chay luc 00:05 UTC — ngay sau khi nen 1D dong.

    1. tai nen moi          4. dong luong: so den luot tai can bang
    2. xep hang thanh khoan 5. so muc tieu -> viec can lam -> dat lenh
    3. RSI(2): thoat, roi vao 6. danh gia lai von, ghi nhat ky
"""
from __future__ import annotations

import math
import threading
import time

import numpy as np

from . import c13 as C13, db, data, delist as DL, executor, pp1x as PX, settings, strategies as ST, swing as SW, volprofile as VP
from .binance import DAY, PublicApi, Trader
from .config import CFG, FEE_BPS


def equity_now() -> float:
    cx = db.connect()
    try:
        r = cx.execute("SELECT value FROM equity WHERE mode=? "
                       "ORDER BY ts DESC LIMIT 1", (mode(),)).fetchone()
        return float(r["value"]) if r else CFG.start_equity
    finally:
        cx.close()


def realised_base(m: str) -> float:
    """Von DA CHOT: von dau + lai/lo moi lenh da dong trong so (moi chien luoc,
    ke ca lenh chot giua cac luot). KHONG noi chuoi tu moc von truoc: moc do da
    gom lai/lo chua chot, cong them mark_to_market nua la dem hai lan."""
    cx = db.connect()
    try:
        r = cx.execute("SELECT COALESCE(SUM(notional * pnl_bps / 1e4), 0) AS s FROM positions "
                       "WHERE mode=? AND open=0 AND pnl_bps IS NOT NULL AND notional IS NOT NULL",
                       (m,)).fetchone()
        return float(CFG.start_equity) + float(r["s"] or 0.0)
    finally:
        cx.close()


def exchange_equity() -> float | None:
    """Von that tren san = so du vi + lai/lo chua chot (totalMarginBalance).
    Gom ca phi, funding, nap/rut ma so bot khong biet. Loi mang → None."""
    t = None
    try:
        t = Trader()
        a = t.account()
        return float(a["totalWalletBalance"]) + float(a["totalUnrealizedProfit"])
    except Exception as e:
        db.log("warn", f"không đọc được vốn trên sàn, dùng vốn theo sổ: {e}")
        return None
    finally:
        if t is not None:
            t.close()


def mode() -> str:
    ready, _ = executor.live_ready()
    return "live" if ready else "paper"


def open_positions(m: str | None = None) -> list:
    cx = db.connect()
    try:
        return [dict(r) for r in cx.execute(
            "SELECT * FROM positions WHERE open=1 AND mode=?", (m or mode(),))]
    finally:
        cx.close()


def _epoch(P: dict) -> int:
    """Moc goc cua lich 7 so — co dinh mot lan de cac so khong bao gio truot."""
    e = db.kv_get("xsmom_epoch")
    if e is None:
        e = int(min(d["t"][0] for d in P.values()))
        db.kv_set("xsmom_epoch", e)
    return int(e)


def planned_exit(p: dict) -> int | None:
    """Gio CHOT du kien (ms UTC) cua mot vi the dong luong: luot chay ke tiep
    ma so cua no den luot tai can bang. Neu luc do ma van duoc chon cung
    chieu thi vi the duoc GIU sang ky moi chu khong dong. RSI(2) khong co
    moc gio — thoat khi RSI > nguong hoac cham stop — tra None."""
    if p.get("strategy") != "xsmom" or p.get("sleeve") is None:
        return None
    e = db.kv_get("xsmom_epoch")
    if e is None:
        return None
    _, X = settings.strat()
    lr = db.kv_get("last_run") or {}
    d = int(lr.get("day") or (p["entry_ts"] // DAY * DAY - DAY)) + DAY
    for _ in range(X["sleeves"] + 1):
        if ST.xsmom_sleeve_of(d, int(e)) == p["sleeve"]:
            break
        d += DAY
    hh, _, mm = CFG.run_at_utc.partition(":")
    # nen ngay d dong luc d + 1 ngay; luot chay luc RUN_AT cua ngay do
    return d + DAY + (int(hh) * 60 + int(mm or 0)) * 60_000


def build_target(P: dict, rank: dict, day: int, cur: list) -> tuple[list, dict]:
    """So MUC TIEU cho hom nay + giai thich tung dong."""
    R, X = settings.strat()
    K, A = settings.risk(), settings.alloc()
    # He so 0 = TAT chien luoc: khong dua vi the nao cua no vao so muc tieu,
    # nen plan() se sinh lenh DONG cho tat ca. Bo qua kieu "khong nhac toi"
    # se de chung mo mai mai ma khong ai tai can bang — dung cai bay da gap
    # voi so lech ngay bi giam.
    r_rsi2 = K["r_usd"] * float(A["rsi2"])
    r_xsmom = K["r_usd"] * float(A["xsmom"])
    target, note = [], {}
    # Ma co thong bao huy niem yet gan day: khong mo lenh MUA moi (app/delist.py).
    # Vi the dang giu va chan BAN khong bi dong cham.
    try:
        nobuy = DL.banned(DL.notices(), int(time.time() * 1000), K["ban_days"])
    except Exception as e:
        nobuy = {}
        db.log("warn", f"đọc danh sách huỷ niêm yết lỗi: {e}")
    hit = sorted(s for s in nobuy if rank.get(s, 10**9) <= max(R["topn"], X["topn"]))
    if hit:
        note["chặn mua (huỷ niêm yết)"] = hit

    def keep_of(p):
        """Vi the dang mo giu nguyen co cu — khong sinh lenh nen chi can khoa."""
        return {"notional": p.get("notional") or 0.0, "r_usd": p.get("r_usd")}

    # ---- RSI(2): giu nhung vi the chua den han thoat ----
    cur_r = [p for p in cur if p["strategy"] == "rsi2"]
    if r_rsi2 <= 0:
        note["rsi2"] = {"tắt": True, "vị thế sẽ đóng": len(cur_r)}
        cur_r = []
    exits = ({id(p): why for p, why in ST.rsi2_exits(P, day, cur_r)}
             if r_rsi2 > 0 else {})
    keep = [p for p in cur_r if id(p) not in exits]
    # Lop cua RSI(2) di trong cot `sleeve`: None = lop goc (giu tuong thich
    # voi vi the mo truoc khi co mua them), 1, 2... = lop mua them. Nho the
    # khoa (chien luoc, so, ma, chieu) cua plan() tach duoc tung lop.
    layers: dict = {}
    for p in keep:
        target.append({"strategy": "rsi2", "sleeve": p.get("sleeve"),
                       "symbol": p["symbol"], "side": 1, "stop": p["stop"],
                       **keep_of(p)})
        layers.setdefault(p["symbol"], set()).add(p.get("sleeve") or 0)
    free = (R["slots"] - len(keep)) if r_rsi2 > 0 else 0
    sig = (ST.rsi2_signals(P, rank, day,
                           {k: len(v) for k, v in layers.items()}, nobuy)
           if r_rsi2 > 0 else [])
    for s in sig[:max(0, free)]:
        stop = ST.rsi2_stop(s["close"], s["atr"])
        how = "6×ATR"
        if R.get("stop_hvn"):
            # Dinh khoi luong gan nhat duoi gia (docs/stop-dinh-day.md). Loi
            # mang hay khong co HVN → giu 6×ATR, khong bo lenh.
            try:
                lv = VP.hvn_below(s["symbol"], int(day) + DAY, s["close"], s["atr"],
                                  int(R["vp_days"]), float(R["vp_bin"]))
            except Exception as e:
                lv = None
                db.log("warn", f"{s['symbol']}: không dựng được volume profile: {e}")
            if lv is not None:
                stop = max(lv - float(R["vp_buf"]) * s["atr"], s["close"] * (1 - R["cap"]))
                how = "HVN"
        # R = khoang cach toi stop theo ty le gia. Co lenh = r_usd / R.
        rf = (s["close"] - stop) / s["close"] if s["close"] > 0 else 0.0
        if rf <= 0:
            continue
        # Stop gan (HVN co khi chi cach 2%) cho lenh rat to. Vuot tran lenh
        # thi THU NHO ve dung tran — rui ro < 1R — chu khong bo ca lenh.
        r_use, notional = r_rsi2, r_rsi2 / rf
        if K["order"] > 0 and notional > K["order"]:
            notional = K["order"]
            r_use = notional * rf
        # chi so lop TRONG nho nhat: lop goc co the da cat lo rieng truoc
        used = layers.get(s["symbol"], set())
        k = next(i for i in range(len(used) + 1) if i not in used)
        target.append({"strategy": "rsi2", "sleeve": k or None,
                       "symbol": s["symbol"],
                       "side": 1, "stop": stop, "r_usd": r_use,
                       "notional": notional,
                       "why": f"RSI(2)={s['rsi']:.1f} · hạng TK #{s['rank']}"
                              f" · R {rf*100:.1f}% ({how})"
                              + (f" · thu về trần {K['order']:.0f} USD = {r_use / r_rsi2:.2f}R"
                                 if r_use < r_rsi2 else "")
                              + (f" · MUA THÊM lớp {k + 1}" if used else "")})
    if r_rsi2 > 0:
        note["rsi2"] = {
            "giữ": len(keep), "thoát": len(exits), "tín hiệu": len(sig),
            "chỗ trống": max(0, free),
            "lý do thoát": sorted({w for w in exits.values()})}

    # ---- dong luong: chi SO DEN LUOT doi, sau so khac giu nguyen ----
    sl = ST.xsmom_sleeve_of(day, _epoch(P))
    cur_x = [p for p in cur if p["strategy"] == "xsmom"]
    if r_xsmom <= 0:
        note["xsmom"] = {"tắt": True, "vị thế sẽ đóng": len(cur_x)}
        cur_x, new = [], None
    # ---- luat phu PP1 (app/pp1x.py), moi luat mot cong tac ----
    F = settings.pp1x()
    kase_x: dict = {}
    if F["kase"] and cur_x:
        try:
            kase_x = PX.kase_exits(P, day, cur_x)
        except Exception as e:
            db.log("error", f"Kase: tính mức lỗi, bỏ qua luật hôm nay: {e}")
        for p in cur_x:
            if id(p) in kase_x:
                p["exit_why"] = kase_x[id(p)]      # plan() mang ly do sang lenh DONG
                db.log("info", f"Kase đóng {p['symbol']} (sổ {p['sleeve']}) · {kase_x[id(p)]}")
    kase_keys = {(p["sleeve"], p["symbol"], p["side"]) for p in cur_x if id(p) in kase_x}
    for p in cur_x:
        # Giam so so trong tab cau hinh se bo roi vi the o so cu: chung khong
        # bao gio trung `sl` nua nen se duoc giu mai mai ma khong ai tai can
        # bang. Khong dua vao so muc tieu => luot nay dong chung lai.
        if p["sleeve"] is not None and p["sleeve"] >= X["sleeves"]:
            continue
        if id(p) in kase_x:                         # Kase: khong dua vao so muc tieu → dong
            continue
        if p["sleeve"] != sl:
            target.append({"strategy": "xsmom", "sleeve": p["sleeve"],
                           "symbol": p["symbol"], "side": p["side"],
                           "stop": None, **keep_of(p)})
    if r_xsmom > 0:
        new = ST.xsmom_target(P, rank, day, nobuy)
    fv = None
    if new and F["fund_veto"]:
        try:
            fv = PX.fund_veto(day)
        except Exception as e:
            db.log("error", f"funding: tính phân vị lỗi, bỏ qua luật hôm nay: {e}")
        if fv and fv.get("active"):
            cut = [x["symbol"] for x in new if x["side"] < 0]
            # Bo han, khong thay bang ma ke tiep — giong engine nghien cuu.
            new = [x for x in new if x["side"] > 0]
            if cut:
                db.log("info", f"funding toàn thị trường cực thấp (phân vị {fv.get('pct')}) · "
                               f"không mở lệnh BÁN động lượng: {', '.join(cut)}")
    bv: dict = {}
    if new and F["bsadf_veto"]:
        try:
            bv = PX.bsadf_veto(P, day, [x["symbol"] for x in new if x["side"] < 0])
        except Exception as e:
            db.log("error", f"BSADF: tính lỗi, bỏ qua luật hôm nay: {e}")
        if bv:
            new = [x for x in new if not (x["side"] < 0 and x["symbol"] in bv)]
            db.log("info", "BSADF > ngưỡng · không mở lệnh BÁN động lượng: "
                           + ", ".join(f"{s} ({v:.2f})" for s, v in bv.items()))
    if new and kase_keys:
        # ma vua bi Kase dong khong mo lai trong cung luot (so den luot hom nay)
        new = [x for x in new if (sl, x["symbol"], x["side"]) not in kase_keys]
    if new:
        for x in new:
            # Khong co stop: 1R = mot lan do lech chuan bat loi qua dung ky
            # nam giu, tuc sigma ngay x sqrt(so ngay giu).
            rf = float(x["vol"]) * math.sqrt(X["hold"])
            if not (rf > 0):
                continue
            target.append({"strategy": "xsmom", "sleeve": sl,
                           "symbol": x["symbol"], "side": x["side"],
                           "stop": None, "r_usd": r_xsmom,
                           "notional": r_xsmom / rf,
                           "why": f"điểm {x['score']:+.2f} · R {rf*100:.1f}%"})
    # ---- windfall (app/pp1wf.py): mo lai lenh bi dong giua ngay o so KHONG den luot ----
    wf_re: list = []
    if r_xsmom > 0 and F.get("wf") and F.get("wf_re"):
        from . import pp1wf as WF          # import muon: pp1wf import runner
        try:
            have = {(t["sleeve"], t["symbol"], t["side"]) for t in target if t["strategy"] == "xsmom"}
            wf_re = WF.reentry_targets(P, day, sl, r_xsmom, have, nobuy)
        except Exception as e:
            db.log("error", f"windfall: mở lại lỗi, bỏ qua hôm nay: {e}")
        target += wf_re
    if r_xsmom > 0:
        note["xsmom"] = {
            "sổ tái cân bằng hôm nay": sl,
            "sổ quá hạn bị đóng": sum(
                1 for p in cur_x if p["sleeve"] is not None
                and p["sleeve"] >= X["sleeves"]),
            "vị thế mới": len(new or []),
            "Kase đóng": sorted(p["symbol"] for p in cur_x if id(p) in kase_x) if F["kase"] else "tắt",
            "funding chặn bán": (bool(fv and fv.get("active")) if fv is not None else
                                 ("tắt" if not F["fund_veto"] else "không cần tính")),
            "BSADF chặn bán": sorted(bv) if F["bsadf_veto"] else "tắt",
            "windfall mở lại": sorted(f"{x['symbol']} (sổ {x['sleeve']})" for x in wf_re) if F.get("wf") else "tắt",
            "sổ khác giữ nguyên": len(cur_x) - sum(
                1 for p in cur_x if p["sleeve"] == sl)}

    # ---- TSVW / DSRM (app/swing.py): stop + chot co dinh, giu toi da 200 ngay ----
    for sname in ("tsvw", "dsrm"):
        r_s = K["r_usd"] * float(A.get(sname, 0.0))
        cur_s = [p for p in cur if p["strategy"] == sname]
        if r_s <= 0:
            note[sname] = {"tắt": True, "vị thế sẽ đóng": len(cur_s)}
            continue
        ex_s = {id(p): why for p, why in SW.exits(P, day, cur_s)}
        held = set()
        for p in cur_s:
            if id(p) in ex_s:
                continue
            held.add(p["symbol"])
            target.append({"strategy": sname, "sleeve": None, "symbol": p["symbol"],
                           "side": p["side"], "stop": p["stop"], "tp": p.get("tp"),
                           **keep_of(p)})
        # Ma vua thoat hom nay khong vao lai cung luot: nghien cuu (mot lenh
        # mot luc) chi xet tin hieu tu nen SAU nen thoat.
        held |= {p["symbol"] for p in cur_s if id(p) in ex_s}
        try:
            sig = SW.signals_today(sname, P, rank, day, held, nobuy)
        except Exception as e:
            sig = []
            db.log("error", f"{SW.NAME[sname]}: tính tín hiệu lỗi: {e}")
        tp_r = float(SW.PARAMS[sname]["tp_r"])
        for x in sig:
            r_use, notional = r_s, r_s / x["rf"]
            if K["order"] > 0 and notional > K["order"]:
                notional = K["order"]
                r_use = notional * x["rf"]
            target.append({"strategy": sname, "sleeve": None, "symbol": x["symbol"],
                           "side": x["side"], "stop": x["stop"], "tp_r": tp_r,
                           "r_usd": r_use, "notional": notional,
                           "why": f"{SW.NAME[sname]} {'MUA' if x['side'] > 0 else 'BÁN'}"
                                  f" · hạng TK #{x['rank']} · R {x['rf']*100:.1f}%"
                                  f" · chốt {tp_r:g}R"
                                  + (f" · thu về trần {K['order']:.0f} USD = {r_use / r_s:.2f}R"
                                     if r_use < r_s else "")})
        note[sname] = {"giữ": len(cur_s) - len(ex_s), "thoát": len(ex_s),
                       "tín hiệu": len(sig),
                       "lý do thoát": sorted({w for w in ex_s.values()})}

    # ---- PP6 VSA 4H (app/vsa.py): mo / dong theo lich 4H rieng. Luot ngay
    # giu nguyen moi vi the cua no (ke ca khi he so = 0: lich 4H tu dong sau
    # 3 nen) — khong dua vao muc tieu thi plan() se dong oan chung.
    cur_v = [p for p in cur if p["strategy"] == "vsa"]
    for p in cur_v:
        target.append({"strategy": "vsa", "sleeve": p.get("sleeve"), "symbol": p["symbol"],
                       "side": p["side"], "stop": None, **keep_of(p)})
    if cur_v:
        note["vsa"] = {"giữ (lịch 4H tự đóng)": len(cur_v)}
    return target, note


def mark_to_market(P: dict, day: int, eq: float,
                   prices: dict | None = None) -> float:
    """Von = phan da chot + lai/lo chua chot cua cac vi the dang mo.

    Phai danh gia theo GIA HIEN TAI, khong phai close cua nen da dong. Vi the
    mo trong chinh luot nay vao o gia thi truong luc chay (sau 00:00 UTC), nen
    lay close hom qua se sinh ra mot khoan lai/lo gia bang dung bien dong trong
    ngay — no tu bien mat hom sau, nhung duong von thi da sai mot moc.
    """
    v = eq
    for p in open_positions():
        px = (prices or {}).get(p["symbol"])
        if not px:
            d = P.get(p["symbol"])
            if d is None:
                continue
            j = min(int(np.searchsorted(d["t"], day)), len(d["t"]) - 1)
            px = float(d["c"][j])
        px = float(px)
        g = (px - p["entry_px"]) / p["entry_px"] * 1e4 * p["side"] - FEE_BPS
        # Ban moi: co lenh luu bang USD. Ban cu luu ty trong von — giu duong
        # du phong de vi the mo truoc khi doi cach ghi so van danh gia duoc.
        notion = p.get("notional")
        v += (float(notion) if notion else eq * (p.get("weight") or 0.0)) * g / 1e4
    return v


def top_symbols(n: int) -> list[str]:
    """Top n thanh khoan cua ngay da dong gan nhat trong kho."""
    bars = data.load_all(settings.strat()[0]["min_bars"])
    P = ST.prep({s: b for s, b in bars.items() if data.is_crypto(b)})
    if not P:
        return []
    rank = ST.ranks_on(P, int(max(d["t"][-1] for d in P.values())))
    return sorted((s for s, r in rank.items() if r <= n), key=lambda s: rank[s])


def _pnl_usd(p: dict, px: float, eq: float) -> tuple[float, float]:
    bps = (px - p["entry_px"]) / p["entry_px"] * 1e4 * p["side"] - FEE_BPS
    notion = p.get("notional")
    return (float(notion) if notion else eq * (p.get("weight") or 0.0)) * bps / 1e4, bps


def reconcile(prices: dict, eq: float) -> float:
    """Dong trong SO nhung vi the san da het (dung an toan da khop, hoac dong
    tay). Khong lam vay thi luot nay gui reduceOnly cho mot vi the khong ton
    tai, va tinh lai/lo cho mot vi the da dong tu lau. Tra lai/lo da chot."""
    t = Trader()
    try:
        ex = {p["symbol"]: float(p["positionAmt"]) for p in t.positions()}
        safe = db.kv_get("safety", {}) or {}
        realised = 0.0
        book = open_positions("live")
        fills: dict = {}

        def closed_at(sym: str, side: int):
            """Gia khop TB cua cac lenh dong (chieu nguoc) SAU lan vao cuoi
            cung cua ma trong so — tuc gia nguoi dung tu cat tren san."""
            if (sym, side) not in fills:
                t0 = max(p["entry_ts"] for p in book
                         if p["symbol"] == sym and p["side"] == side)
                osd = "SELL" if side > 0 else "BUY"
                try:
                    tr = [x for x in t.user_trades(
                              sym, max(t0, int(time.time() * 1000) - 7 * DAY + 60_000))
                          if x.get("side") == osd and int(x.get("time", 0)) > t0]
                except Exception:
                    tr = []
                q = sum(float(x["qty"]) for x in tr)
                fills[(sym, side)] = (
                    sum(float(x["price"]) * float(x["qty"]) for x in tr) / q
                    if q > 0 else None,
                    max((int(x["time"]) for x in tr), default=None))
            return fills[(sym, side)]

        for p in book:
            amt = ex.get(p["symbol"], 0.0)
            if amt != 0 and (amt > 0) == (p["side"] > 0):
                continue
            px, why = prices.get(p["symbol"]), "sàn không còn vị thế"
            ts = int(time.time() * 1000)
            fpx, fts = closed_at(p["symbol"], p["side"])
            if fpx:
                px, why, ts = fpx, "đóng tay trên sàn", fts or ts
            s = safe.get(p["symbol"])
            if s and s.get("algoId"):
                try:
                    a = t.algo_order(s["algoId"])
                    if float(a.get("actualPrice") or 0) > 0:
                        px, why = float(a["actualPrice"]), (
                            "dừng tay trên sàn" if s.get("src") == "tay"
                            else "dừng an toàn trên sàn")
                except Exception:
                    pass
            if not px:
                db.log("error", f"{p['symbol']}: sàn đã hết vị thế nhưng không có "
                                f"giá để chốt sổ — để nguyên")
                continue
            usd, bps = _pnl_usd(p, px, eq)
            realised += usd
            with db.tx() as cx:
                cx.execute("UPDATE positions SET open=0, exit_px=?, exit_ts=?,"
                           " exit_why=?, pnl_bps=? WHERE id=?",
                           (px, ts, why, bps, p["id"]))
            db.log("warn", f"{p['symbol']}: {why} · chốt sổ ở {px:g} · "
                           f"{usd:+.2f} USD")
        realised += _reconcile_qty(t, ex, eq)
        return realised
    finally:
        t.close()


def _reconcile_qty(t: Trader, ex: dict, eq: float) -> float:
    """So CUNG CHIEU nhung nhieu hon san (vd. lenh DONG da khop ma luot chay
    bao loi vi doc trang thai hong): chot so vi the co lenh DONG loi khop dung
    phan thieu, theo gia khop tren san. Khong ghep duoc thi chi bao loi — de
    nguyen thi luot sau gui reduceOnly cat nham vi the that cua so khac."""
    import re
    realised = 0.0
    book = open_positions("live")
    for sym in {p["symbol"] for p in book}:
        mine = [p for p in book if p["symbol"] == sym]
        held = sum(p["side"] * p["qty"] for p in mine)
        amt = ex.get(sym, 0.0)
        gap = abs(held) - abs(amt)
        if amt == 0 or (amt > 0) != (held > 0) or gap <= 1e-9 + 1e-6 * abs(held):
            continue
        for p in mine:
            if gap <= 1e-9 + 1e-6 * abs(held):
                break
            if abs(p["qty"] - gap) > 1e-9 + 1e-3 * p["qty"] and p["qty"] > gap:
                continue
            o = db.connect().execute(
                "SELECT ts, resp FROM orders WHERE mode='live' AND action='CLOSE'"
                " AND status IN ('lỗi','không khớp') AND symbol=? AND strategy=?"
                " AND sleeve IS ? AND ts>=? ORDER BY ts DESC LIMIT 1",
                (sym, p["strategy"], p["sleeve"], p["entry_ts"])).fetchone()
            m_ = re.search(r"lệnh (\d+)", (o["resp"] or "")) if o else None
            if not m_:
                continue
            try:
                tr = [x for x in t.user_trades(sym, int(o["ts"]) - 3600_000)
                      if str(x.get("orderId")) == m_.group(1)]
            except Exception:
                tr = []
            q = sum(float(x["qty"]) for x in tr)
            if abs(q - p["qty"]) > 1e-9 + 1e-3 * p["qty"]:
                continue
            px = sum(float(x["price"]) * float(x["qty"]) for x in tr) / q
            ts = max(int(x["time"]) for x in tr)
            usd, bps = _pnl_usd(p, px, eq)
            realised += usd
            gap -= p["qty"]
            with db.tx() as cx:
                cx.execute("UPDATE positions SET open=0, exit_px=?, exit_ts=?,"
                           " exit_why=?, pnl_bps=? WHERE id=?",
                           (px, ts, "lệnh đóng đã khớp (lượt chạy báo lỗi)",
                            bps, p["id"]))
            db.log("warn", f"{sym}: lệnh đóng {m_.group(1)} thực ra đã khớp · "
                           f"chốt sổ ở {px:g} · {usd:+.2f} USD")
        if gap > 1e-9 + 1e-6 * abs(held):
            db.log("error", f"{sym}: sổ {abs(held):g} nhiều hơn sàn {abs(amt):g} "
                            "— KIỂM TAY, lượt sau có thể đóng nhầm vị thế sổ khác")
    return realised


def reconcile_now() -> int:
    """Doi chieu so voi san NGOAI luot chay (dinh ky / bam tay), de vi the
    nguoi dung tu cat bien khoi trang ngay. Lai/lo da chot cong don vao
    `realised_pending`, luot chay ke tiep cong vao von. Tra so vi the da chot."""
    if not RUN_LOCK.acquire(blocking=False):
        return 0                          # luot chay dang lam viec nay roi
    api = None
    try:
        before = len(open_positions("live"))
        api = PublicApi()
        r = reconcile(api.prices(), equity_now())
        n = before - len(open_positions("live"))
        if n:
            db.kv_set("realised_pending",
                      float(db.kv_get("realised_pending", 0) or 0) + r)
            safety_now()
        return n
    finally:
        if api is not None:
            api.close()
        RUN_LOCK.release()


def safety_now(filt: dict | None = None) -> None:
    """Dong bo dung an toan tren san voi so hien tai. Loi chi ghi nhat ky."""
    t = api = None
    try:
        t = Trader()
        if filt is None:
            api = PublicApi()
            filt = data.filters(api)
        executor.sync_safety(t, open_positions("live"), filt)
    except Exception as e:
        db.log("error", f"đồng bộ dừng an toàn lỗi: {e}")
    finally:
        for c in (t, api):
            if c is not None:
                c.close()


# Mot luot chay va mot cu «ep lenh» khong duoc chay chong len nhau: ca hai
# doc so roi dat lenh, chay chong thi mot lenh co the vao hai lan.
RUN_LOCK = threading.Lock()


def _book_open(cx, a: dict, m: str) -> None:
    # TSVW / DSRM: muc chot tinh tu GIA KHOP (nghien cuu: e + k·(e − stop)).
    tp = a.get("tp")
    if a.get("tp_r") and a.get("stop") and a.get("px"):
        tp = a["px"] + a["side"] * float(a["tp_r"]) * abs(a["px"] - a["stop"])
    cx.execute(
        "INSERT INTO positions(strategy,sleeve,symbol,side,qty,"
        "weight,notional,r_usd,entry_px,entry_ts,stop,tp,mode,open)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
        (a["strategy"], a.get("sleeve"), a["symbol"], a["side"],
         a.get("qty", 0.0), a.get("weight"),
         a.get("notional"), a.get("r_usd"), a["px"],
         int(time.time() * 1000), a.get("stop"), tp, m))


_KEEP = ("strategy", "sleeve", "symbol", "side", "stop", "tp", "tp_r", "notional",
         "r_usd", "weight", "why")


def _save_blocked(run_id: int, day: int, m: str, blocked: list) -> None:
    """Luu lenh bi chan cua luot MOI NHAT de UI hien va cho ep vao."""
    items = [{k: a.get(k) for k in _KEEP} for a in blocked
             if a.get("action") == "OPEN"]
    db.kv_set("blocked", {"run_id": run_id, "day": day, "mode": m,
                          "ts": int(time.time() * 1000), "items": items})


def force_blocked(i: int, run_id: int) -> dict:
    """Ep vao MOT lenh bi chan cua luot moi nhat, BO QUA tran rui ro.

    Van giu cac chot khong the bo: dung che do luc chan, chua co vi the cung
    khoa, khong nguoc chieu vi the dang giu (san mot chieu), va khong chay
    chong voi mot luot dang chay.
    """
    if not RUN_LOCK.acquire(blocking=False):
        raise RuntimeError("đang có lượt chạy — đợi xong rồi bấm lại")
    api = None
    try:
        b = db.kv_get("blocked") or {}
        items = b.get("items") or []
        if b.get("run_id") != run_id or not (0 <= i < len(items)):
            raise RuntimeError("danh sách bị chặn đã đổi — tải lại trang")
        a = items[i]
        if a.get("forced"):
            raise RuntimeError("lệnh này đã được ép vào rồi")
        m = mode()
        if m != b.get("mode"):
            raise RuntimeError(f"lệnh bị chặn ở chế độ {b.get('mode')}, "
                               f"giờ đang là {m}")
        cur = open_positions(m)
        k = (a["strategy"], a.get("sleeve"), a["symbol"], a["side"])
        if any((p["strategy"], p.get("sleeve"), p["symbol"], p["side"]) == k
               for p in cur):
            raise RuntimeError("vị thế này đã có trong sổ")
        if m == "live" and any(p["symbol"] == a["symbol"]
                               and p["side"] != a["side"] for p in cur):
            raise RuntimeError("đang giữ chiều ngược lại trên mã này — sàn "
                               "chạy một chiều, không ép được")
        api = PublicApi()
        prices = api.prices()
        filt = data.filters(api) if m == "live" else {}
        act = {"action": "OPEN", **{x: a.get(x) for x in _KEEP}}
        done = executor.execute(run_id, [act], equity_now(), prices, filt, m)
        d = done[0] if done else {"status": "lỗi"}
        ok = d.get("status") not in ("lỗi", "bỏ qua")
        if ok:
            with db.tx() as cx:
                _book_open(cx, d, m)
            items[i] = {**a, "forced": int(time.time() * 1000), "px": d["px"]}
            db.kv_set("blocked", {**b, "items": items})
            if m == "live":
                safety_now(filt)
        db.log("warn" if ok else "error",
               f"ÉP LỆNH bị chặn: {a['symbol']} "
               f"{'MUA' if a['side'] > 0 else 'BÁN'} {a.get('notional') or 0:.0f} USD"
               f" (lý do chặn: {a.get('why')}) → {d.get('status')}")
        return {"status": d.get("status"), "px": d.get("px"),
                "symbol": a["symbol"]}
    finally:
        if api is not None:
            api.close()
        RUN_LOCK.release()


def run_once(force: bool = False) -> dict:
    with RUN_LOCK:
        return _run_once(force)


def _run_once(force: bool = False) -> dict:
    t0 = time.time()
    m = mode()
    api = PublicApi()
    run_id = None
    try:
        with db.tx() as cx:
            cur = cx.execute(
                "INSERT INTO runs(ts,bar_ts,mode,status,detail) "
                "VALUES(?,?,?,?,?)",
                (int(time.time() * 1000), 0, m, "đang chạy", ""))
            run_id = cur.lastrowid

        # Chi cap nhat ma DANG niem yet. Ma da huy thi lich su dung yen —
        # goi API cho chung chi ton tran trong so va luon tra ve rong.
        syms = data.live_symbols(api)
        data.refresh(api, syms)
        bars = data.load_all(settings.strat()[0]["min_bars"])
        bars = {s: b for s, b in bars.items() if data.is_crypto(b)}
        P = ST.prep(bars)
        if not P:
            raise RuntimeError("kho nến rỗng — chưa tải được dữ liệu")
        day = int(max(d["t"][-1] for d in P.values()))
        rank = ST.ranks_on(P, day)
        # Nen 1H cho top 20 — kho cho tab «Tinh lich su» mo phong stop HVN.
        # Lenh that van tai 1H truc tiep luc dung profile (volprofile.hvn_below).
        try:
            data.refresh_1h(api, [s_ for s_, r_ in rank.items() if r_ <= 20])
        except Exception as e:
            db.log("warn", f"cập nhật nến 1H lỗi: {e}")
        # Thong bao huy niem yet moi — hai trang moi nhat la du cho mot ngay.
        # Loi mang khong chan luot chay: danh sach cu van con trong kho.
        try:
            DL.refresh(2)
            DL.refresh_monitor(2)
        except Exception as e:
            db.log("warn", f"cập nhật thông báo huỷ niêm yết / thẻ Monitoring lỗi: {e}")

        prices = api.prices()
        # eq = von DA CHOT theo so. Lenh chot giua cac luot (doi chieu 5 phut,
        # PP6 VSA) da nam trong so nen hai bien kv cu chi con duoc xoa ve 0.
        eq = realised_base(m)
        if m == "live":
            eq += reconcile(prices, eq)
        db.kv_set("realised_pending", 0.0)
        db.kv_set(f"vsa_realised:{m}", 0.0)
        # chot giua cac luot (pp1tp / pp1wf / swingtp) da nam trong realised_base
        # (lenh da dong trong so) — cong them `tp_realised` nua la dem hai lan
        db.kv_set(f"tp_realised:{m}", 0.0)
        # C13: lenh limit dat o luot truoc — khop thi ghi so (luot nay dong lai)
        try:
            C13.settle(m, P, day)
        except Exception as e:
            db.log("error", f"C13: đối chiếu lệnh limit lỗi: {e}")
        cur_pos = open_positions(m)
        target, note = build_target(P, rank, day, cur_pos)
        n13 = len(C13.exits(cur_pos))           # vi the C13 giu dung mot ngay → dong
        if n13:
            note["c13"] = {"đóng": n13}
        filt = data.filters(api) if m == "live" else {}

        actions = executor.plan(target, cur_pos)
        # vi the C13 dong het trong luot nay — khong tinh vao tran so lenh / phoi nhiem
        keep_pos = [p for p in cur_pos if p["strategy"] != "c13"]
        # Tran theo von DANH GIA LAI: chay that lay so cua san, giay tinh tu so.
        eq_now = (exchange_equity() if m == "live" else None) or mark_to_market(P, day, eq, prices)
        allowed, blocked = executor.apply_caps(
            actions, eq_now, prices, len(keep_pos),
            sum(float(p.get("notional") or 0.0) for p in keep_pos))
        if m == "live":          # so giay giu nguyen hanh vi nhu backtest
            # SAU tran: lenh mo bi chan thi khong dong oan vi the nguoc chieu
            allowed, clash = executor.one_way(allowed, cur_pos)
            blocked += clash
        done = executor.execute(run_id, allowed, eq, prices, filt, m)

        # ---- cap nhat so sach ----
        # CHI ghi so cho lenh thuc su khop. Lenh bi san tu choi ("loi") hoac
        # bo qua vi duoi muc toi thieu ("bo qua") khong duoc coi la da mo /
        # da dong: ghi vao la so noi bo va san lech nhau ngay tu luot dau, va
        # luot sau se gui reduceOnly dong mot vi the khong ton tai.
        filled = [a for a in done if a.get("status") not in ("lỗi", "bỏ qua", "không khớp")]
        failed = [a for a in done if a.get("status") in ("lỗi", "bỏ qua", "không khớp")]
        realised = 0.0
        with db.tx() as cx:
            for a in filled:
                if a["action"] == "CLOSE":
                    p = next((x for x in cur_pos
                              if x["symbol"] == a["symbol"]
                              and x["strategy"] == a["strategy"]
                              and x.get("sleeve") == a.get("sleeve")
                              and x["side"] == a["side"]), None)
                    if not p:
                        continue
                    bps = ((a["px"] - p["entry_px"]) / p["entry_px"] * 1e4
                           * p["side"] - FEE_BPS)
                    notion = p.get("notional")
                    realised += (float(notion) if notion
                                 else eq * (p.get("weight") or 0.0)) * bps / 1e4
                    cx.execute(
                        "UPDATE positions SET open=0, exit_px=?, exit_ts=?,"
                        " exit_why=?, pnl_bps=? WHERE id=?",
                        (a["px"], int(time.time() * 1000),
                         a.get("exit_why") or "mục tiêu đổi",
                         bps, p["id"]))
                else:
                    _book_open(cx, a, m)
        _save_blocked(run_id, day, m, blocked)
        # windfall: muc mo lai da den luot hom nay (mo duoc, bi chan, hay so den luot) → bo
        try:
            from . import pp1wf as WF
            WF.consume(day + DAY)
        except Exception as e:
            db.log("warn", f"windfall: dọn danh sách mở lại lỗi: {e}")
        # C13: treo lenh limit mua cho nen ke tiep (sau khi so da ghi xong)
        try:
            if C13.r_usd() > 0:
                try:
                    nob = DL.banned(DL.notices(), int(time.time() * 1000), settings.risk()["ban_days"])
                except Exception:
                    nob = {}
                note["c13"] = {**note.get("c13", {}),
                               **C13.place(m, P, day, rank, eq + realised, nob, filt)}
            else:
                n_ = C13.cancel_all(m)
                if n_:
                    db.log("info", f"C13 đang tắt: huỷ {n_} lệnh limit còn treo")
        except Exception as e:
            db.log("error", f"C13: đặt lệnh limit lỗi: {e}")
        eq += realised          # lai/lo da chot la USD, khong phai ty le
        if m == "live":
            safety_now(filt)    # sau khi so da ghi vi the moi
        mtm = (exchange_equity() if m == "live" else None) or mark_to_market(P, day, eq, prices)
        with db.tx() as cx:
            cx.execute("INSERT OR REPLACE INTO equity(ts,mode,value) "
                       "VALUES(?,?,?)", (day, m, mtm))
            op = open_positions(m)
            gross = sum(float(x.get("notional") or 0.0) for x in op)
            cx.execute("UPDATE runs SET n_open=?, gross=? WHERE id=?",
                       (len(op), gross, run_id))
            cx.execute("UPDATE runs SET bar_ts=?, status=?, detail=? WHERE id=?",
                       (day, "xong",
                        f"{len(filled)} lệnh · {len(blocked)} bị chặn"
                        + (f" · {len(failed)} KHÔNG KHỚP" if failed else "")
                        + f" · vốn {mtm:,.2f} USD", run_id))
        db.kv_set("last_run", {"ts": int(time.time() * 1000), "day": day,
                               "mode": m, "orders": len(filled),
                               "blocked": len(blocked), "failed": len(failed),
                               "equity": mtm,
                               "secs": round(time.time() - t0, 1)})
        for a in failed:
            db.log("warn", f"không khớp, bỏ khỏi sổ: {a['action']} "
                           f"{a['symbol']} ({a.get('status')})")
        if CFG.c13_paper:            # so giay C13 — chi ghi, khong dat lenh (app/c13.py)
            try:
                C13.run_once(P, day)
            except Exception as e:
                db.log("warn", f"sổ giấy C13 lỗi: {e}")
        db.log("info", f"luợt chạy {run_id} xong · chế độ {m} · {len(done)} lệnh"
                       f" · vốn {mtm:,.2f} USD")
        return {"run_id": run_id, "day": day, "mode": m, "note": note,
                "actions": filled, "failed": failed, "blocked": blocked,
                "equity": mtm}
    except Exception as e:
        db.log("error", f"lượt chạy hỏng: {e}")
        if run_id:
            with db.tx() as cx:
                cx.execute("UPDATE runs SET status=?, detail=? WHERE id=?",
                           ("hỏng", str(e)[:500], run_id))
        raise
    finally:
        api.close()
