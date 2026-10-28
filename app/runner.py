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

from . import db, data, executor, settings, strategies as ST, volprofile as VP
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
                           {k: len(v) for k, v in layers.items()})
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
    for p in cur_x:
        # Giam so so trong tab cau hinh se bo roi vi the o so cu: chung khong
        # bao gio trung `sl` nua nen se duoc giu mai mai ma khong ai tai can
        # bang. Khong dua vao so muc tieu => luot nay dong chung lai.
        if p["sleeve"] is not None and p["sleeve"] >= X["sleeves"]:
            continue
        if p["sleeve"] != sl:
            target.append({"strategy": "xsmom", "sleeve": p["sleeve"],
                           "symbol": p["symbol"], "side": p["side"],
                           "stop": None, **keep_of(p)})
    if r_xsmom > 0:
        new = ST.xsmom_target(P, rank, day)
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
    if r_xsmom > 0:
        note["xsmom"] = {
            "sổ tái cân bằng hôm nay": sl,
            "sổ quá hạn bị đóng": sum(
                1 for p in cur_x if p["sleeve"] is not None
                and p["sleeve"] >= X["sleeves"]),
            "vị thế mới": len(new or []),
            "sổ khác giữ nguyên": len(cur_x) - sum(
                1 for p in cur_x if p["sleeve"] == sl)}
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
        for p in open_positions("live"):
            amt = ex.get(p["symbol"], 0.0)
            if amt != 0 and (amt > 0) == (p["side"] > 0):
                continue
            px, why = prices.get(p["symbol"]), "sàn không còn vị thế"
            s = safe.get(p["symbol"])
            if s and s.get("algoId"):
                try:
                    a = t.algo_order(s["algoId"])
                    if float(a.get("actualPrice") or 0) > 0:
                        px, why = float(a["actualPrice"]), "dừng an toàn trên sàn"
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
                           (px, int(time.time() * 1000), why, bps, p["id"]))
            db.log("warn", f"{p['symbol']}: {why} · chốt sổ ở {px:g} · "
                           f"{usd:+.2f} USD")
        return realised
    finally:
        t.close()


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
    cx.execute(
        "INSERT INTO positions(strategy,sleeve,symbol,side,qty,"
        "weight,notional,r_usd,entry_px,entry_ts,stop,mode,open)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)",
        (a["strategy"], a.get("sleeve"), a["symbol"], a["side"],
         a.get("qty", 0.0), a.get("weight"),
         a.get("notional"), a.get("r_usd"), a["px"],
         int(time.time() * 1000), a.get("stop"), m))


_KEEP = ("strategy", "sleeve", "symbol", "side", "stop", "notional", "r_usd",
         "weight", "why")


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

        prices = api.prices()
        eq = equity_now()
        if m == "live":
            eq += reconcile(prices, eq)
        cur_pos = open_positions(m)
        target, note = build_target(P, rank, day, cur_pos)
        filt = data.filters(api) if m == "live" else {}

        actions = executor.plan(target, cur_pos)
        clash = []
        if m == "live":          # so giay giu nguyen hanh vi nhu backtest
            actions, clash = executor.one_way(actions, cur_pos)
        allowed, blocked = executor.apply_caps(
            actions, eq, prices, len(cur_pos),
            sum(float(p.get("notional") or 0.0) for p in cur_pos))
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
                        (a["px"], int(time.time() * 1000), "mục tiêu đổi",
                         bps, p["id"]))
                else:
                    _book_open(cx, a, m)
        _save_blocked(run_id, day, m, blocked)
        eq += realised          # lai/lo da chot la USD, khong phai ty le
        if m == "live":
            safety_now(filt)    # sau khi so da ghi vi the moi
        mtm = mark_to_market(P, day, eq, prices)
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
