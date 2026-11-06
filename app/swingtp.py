"""Chot loi TSVW / DSRM giua cac luot ngay — kiem moi nen 15m.

Luot ngay (runner, swing.exits) chi thay muc chot loi qua high/low nen 1D va
dong o gia luc 00:05 hom sau: gia cham muc roi quay dau trong ngay thi hut lai.
Tren san chi co dung an toan (cat lo), KHONG co lenh chot loi treo san.

Luat: moi nen 15m vua dong (lich phut 1/16/31/46), voi moi vi the tsvw / dsrm
dang mo co `tp`, xet cac nen 15m tu luc vao (hoac lan kiem truoc) toi nen vua
dong: high ≥ tp (MUA) / low ≤ tp (BAN) → dong toan bo o gia thi truong, qua
executor nhu luot ngay. Nen cham CA muc cat lo thi bo qua — dung an toan tren
san quyet dinh, doi chieu so (reconcile) se chot so.
Luot ngay van giu swing.exits theo nen 1D lam luoi do neu lich 15m bi lo.
Lai/lo nam trong so (realised_base); `tp_realised` chi de tab hien thi.
"""
from __future__ import annotations

import time

from . import db, executor, data, runner
from .binance import PublicApi
from .config import FEE_BPS

TF, STEP = "15m", 900_000
KEY_SEEN = "swingtp_seen"          # {pos_id: open_ms cua nen 15m cuoi da xet}


def run_once() -> dict:
    st = {"t": int(time.time() * 1000), "checked": 0, "closed": [], "errors": [], "skipped": []}
    m = runner.mode()
    st["mode"] = m
    if not [p for p in runner.open_positions(m) if p["strategy"] in ("tsvw", "dsrm") and p.get("tp")]:
        db.kv_set("swingtp_last", st)
        return st
    if not runner.RUN_LOCK.acquire(timeout=600):
        db.log("warn", "chốt lời TSVW/DSRM: lượt ngày giữ khoá quá 10 phút — bỏ lượt này")
        return st
    api = PublicApi()
    try:
        now = int(time.time() * 1000)
        close_ms = now // STEP * STEP           # nen [close_ms − 15m, close_ms) vua dong
        book = [p for p in runner.open_positions(m)
                if p["strategy"] in ("tsvw", "dsrm") and p.get("tp")]
        seen = {str(k): int(v) for k, v in (db.kv_get(KEY_SEEN, {}) or {}).items()}
        acts, seen2 = [], {}
        for p in book:
            pid = str(p["id"])
            side, tp, stop = int(p["side"]), float(p["tp"]), p.get("stop")
            # nen chua gio vao tro di; da xet roi thi tu nen ke tiep
            t0 = max(int(p["entry_ts"]) // STEP * STEP, seen.get(pid, -STEP) + STEP)
            if t0 >= close_ms:
                seen2[pid] = seen.get(pid, t0 - STEP)
                continue
            try:
                k = api.klines_iv(p["symbol"], TF, t0, min(1500, (close_ms - t0) // STEP))
            except Exception as e:
                st["errors"].append(f"{p['symbol']}: nến {TF} lỗi {e}")
                seen2[pid] = seen.get(pid, t0 - STEP)
                continue
            k = [x for x in k if int(x[0]) < close_ms and int(x[6]) < now]
            if not k:
                seen2[pid] = seen.get(pid, t0 - STEP)
                continue
            st["checked"] += 1
            seen2[pid] = int(k[-1][0])
            for x in k:
                hi, lo = float(x[2]), float(x[3])
                if not ((side > 0 and hi >= tp) or (side < 0 and lo <= tp)):
                    continue
                if stop and ((side > 0 and lo <= float(stop)) or (side < 0 and hi >= float(stop))):
                    st["skipped"].append(f"{p['symbol']}: nến chạm cả cắt lỗ — để dừng trên sàn")
                    break
                acts.append({"action": "CLOSE", **p,
                             "exit_why": f"chốt lời {p['strategy'].upper()} · nến {TF} chạm {tp:g}"})
                break
        if acts:
            prices = api.prices()
            eq = runner.equity_now()
            filt = data.filters(api) if m == "live" else {}
            done = executor.execute(None, acts, eq, prices, filt, m)
            realised = 0.0
            msgs = []
            with db.tx() as cx:
                for a in done:
                    if a.get("status") in ("lỗi", "bỏ qua", "không khớp"):
                        st["errors"].append(f"{a['symbol']}: {a.get('status')}")
                        pid = str(a["id"])          # dong hong: lan sau xet lai cac nen nay
                        if pid in seen:
                            seen2[pid] = seen[pid]
                        else:
                            seen2.pop(pid, None)
                        continue
                    bps = (a["px"] - a["entry_px"]) / a["entry_px"] * 1e4 * a["side"] - FEE_BPS
                    usd = float(a.get("notional") or 0) * bps / 1e4
                    realised += usd
                    cx.execute("UPDATE positions SET open=0, exit_px=?, exit_ts=?, exit_why=?, pnl_bps=? WHERE id=?",
                               (a["px"], int(time.time() * 1000), a["exit_why"], bps, a["id"]))
                    st["closed"].append({"symbol": a["symbol"], "strategy": a["strategy"], "side": a["side"],
                                         "px": a["px"], "bps": round(bps, 1), "usd": round(usd, 2),
                                         "why": a["exit_why"]})
                    msgs.append(f"{a['exit_why']} · {a['symbol']} {a['px']:g} · "
                                f"{bps:+.0f} bps · {usd:+.2f} USD")
            for x in msgs:                      # ghi log SAU khi dong giao dich (log mo ket noi rieng)
                db.log("info", x)
            if realised:
                key = f"tp_realised:{m}"
                db.kv_set(key, float(db.kv_get(key, 0) or 0) + realised)
            st["realised"] = realised
            if m == "live" and st["closed"]:
                runner.safety_now(filt)
        db.kv_set(KEY_SEEN, seen2)
    finally:
        api.close()
        runner.RUN_LOCK.release()
        db.kv_set("swingtp_last", st)
    return st
