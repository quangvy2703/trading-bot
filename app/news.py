"""So giay theo tin cua Binance — CHI GHI, KHONG BAO GIO DAT LENH.

Module nay khong import Trader va khong goi endpoint co ky nao ngoai WebSocket
thong bao (chi doc). Muc dich (docs/huy-niem-yet.md):
  1. DO DO TRE tu gio dang bai toi luc bot nhan duoc tin. Moi thong bao (moi
     muc, khong chi huy niem yet) la mot mau do. Gia perp roi tu giay thu 3
     sau tin go spot, nen tre > ~2 giay la chien luoc go spot vo dung.
  2. Ghi lenh BAN KHONG GIA cho hai o da dat luat:
       S  "Binance Will Delist X …"            — lai 15% thi doi stop ve gia
                                                 vao (hoa von), giu 24 gio
       M  "… Monitoring Tag to Include X …"    — khong stop, giu 24 gio
     F (go perp) chi ghi tin, khong mo lenh gia (truot luat).

Hai nguon, nguon nao toi truoc thi tinh:
  ws   wss://api.binance.com/sapi/wss, topic com_announcement_en — can mot
       khoa API RIENG chi doc (NEWS_API_KEY / NEWS_API_SECRET). Khong dung khoa
       giao dich: khoa do bi san tu choi o day (-2015), va mot luong doc tin
       khong co ly do cam khoa dat lenh.
  poll API CMS muc 161 + 49 moi 30 giay — du phong khi WebSocket dut
Gia lenh gia: bookTicker perp ngay luc nhan tin (ban o bid, mua lai o ask),
doc moi giay khi co lenh mo. Chi phi 40 bps nhu nghien cuu. Chua tinh funding.
Do tre dung dong ho may + do lech voi dong ho Binance (/fapi/v1/time).
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
import secrets
import time

import httpx

from . import db, delist as DL
from .binance import DAY
from .config import CFG

WS = "wss://api.binance.com/sapi/wss"
TOPIC = "com_announcement_en"
G_ARM, HOLD, COST = 0.15, DAY, 40.0
M_RE = re.compile(r"(?i)monitoring tag to (?:include\s+)?(.+?)"
                  r"(?:,?\s+(?:and\s+)?remove\b|\s+on\s+\d{4}-|$)")
_OFF = [0.0]                         # dong ho Binance − dong ho may (ms)
_LOCK: list = [None]                 # asyncio.Lock, tao trong vong lap dang chay


def now_ms() -> float:
    return time.time() * 1000 + _OFF[0]


def classify(title: str, body: str = "") -> list[tuple[str, str]]:
    ev = DL.parse(title)
    if ev == [("F*", "")]:
        ev = [("F", b) for b in DL.perp_syms(body or "")]
    if not ev:
        m = M_RE.search(title)
        if m:
            ev = [("M", x) for x in re.findall(r"\b[0-9A-Z]{1,15}\b", m.group(1))
                  if x not in DL.STOP]
    return ev


def _status(**kw) -> None:
    s = db.kv_get("news_status", {}) or {}
    s.update(kw)
    db.kv_set("news_status", s)


async def _book(cx: httpx.AsyncClient, sym: str | None = None):
    r = await cx.get(f"{CFG.public_rest}/fapi/v1/ticker/bookTicker",
                     params={"symbol": sym} if sym else None)
    r.raise_for_status()
    return r.json()


async def handle(cx, catalog: int, title: str, body: str, t_pub: int, t_recv: float, src: str):
    key = hashlib.sha1(f"{title.strip()}|{int(t_pub) // 1000}".encode()).hexdigest()
    ev = classify(title, body)
    async with _LOCK[0]:
        with db.tx() as c:
            n = c.execute("INSERT OR IGNORE INTO news(key, catalog, title, t_pub, t_recv, src, kinds)"
                          " VALUES(?,?,?,?,?,?,?)",
                          (key, int(catalog or 0), title, int(t_pub), int(t_recv), src,
                           ",".join(f"{k}:{b}" for k, b in ev))).rowcount
        if not n or not ev:
            return
        lat = (t_recv - t_pub) / 1000
        for kind, base in ev:
            sym = base + "USDT"
            if kind == "F":
                db.log("info", f"TIN gỡ perp {sym} ({src}, trễ {lat:.1f} s) — chỉ ghi, không mở lệnh giấy")
                continue
            cx_ = db.connect()
            try:
                dup = cx_.execute("SELECT 1 FROM news_paper WHERE symbol=? AND kind=? AND t_pub>?",
                                  (sym, kind, int(t_pub) - 3 * DAY)).fetchone()
            finally:
                cx_.close()
            if dup:
                continue
            try:
                b = await _book(cx, sym)
                px = float(b["bidPrice"])
            except Exception:
                px = 0.0
            t_in = now_ms()
            if px <= 0:
                db.log("info", f"TIN {kind} {sym} ({src}, trễ {lat:.1f} s) — không có perp, bỏ")
                continue
            with db.tx() as c:
                c.execute("INSERT OR IGNORE INTO news_paper(news_key, kind, symbol, t_pub, t_recv,"
                          " t_entry, entry_px, low) VALUES(?,?,?,?,?,?,?,?)",
                          (key, kind, sym, int(t_pub), int(t_recv), int(t_in), px, px))
            db.log("info", f"TIN {kind} {sym}: sổ giấy BÁN {px:g} · trễ nhận {lat:.1f} s"
                           f" · trễ vào {(t_in - t_pub) / 1000:.1f} s ({src})")


async def ws_loop(cx):
    back = 5
    while True:
        if not (CFG.news_api_key and CFG.news_api_secret):
            _status(ws="chưa có khoá đọc NEWS_API_KEY / NEWS_API_SECRET — chỉ đọc API CMS mỗi 30 giây")
            await asyncio.sleep(600)
            continue
        import websockets
        p = {"random": secrets.token_hex(16), "recvWindow": 30000,
             "timestamp": int(now_ms()), "topic": TOPIC}
        q = "&".join(f"{k}={p[k]}" for k in sorted(p))
        sig = hmac.new(CFG.news_api_secret.encode(), q.encode(), hashlib.sha256).hexdigest()
        try:
            async with websockets.connect(f"{WS}?{q}&signature={sig}",
                                          additional_headers={"X-MBX-APIKEY": CFG.news_api_key},
                                          ping_interval=None, open_timeout=20,
                                          max_size=2 ** 22) as ws:
                t0 = time.time()
                _status(ws="đã nối", ws_since=int(t0 * 1000))
                back, refused = 5, False

                async def pinger():
                    while True:
                        await asyncio.sleep(25)
                        await ws.ping(b"")
                pt = asyncio.create_task(pinger())
                try:
                    async for raw in ws:
                        t_recv = now_ms()
                        m = json.loads(raw)
                        if m.get("type") == "DATA":
                            d = json.loads(m["data"])
                            _status(ws_last=int(t_recv))
                            await handle(cx, d.get("catalogId"), d.get("title", ""),
                                         d.get("body", ""), int(d["publishDate"]), t_recv, "ws")
                        elif m.get("type") == "COMMAND" and m.get("data") != "SUCCESS":
                            # Khoa sai / IP bi chan: san dong ket noi ngay. Noi lai
                            # lien tuc co the bi chan IP — nghi 30 phut.
                            _status(ws=f"sàn từ chối: {str(m.get('data'))[:120]}")
                            db.log("warn", f"WebSocket tin bị từ chối: {str(m)[:200]} — thử lại sau 30 phút")
                            back, refused = 1800, True
                            break
                        if time.time() - t0 > 23 * 3600:      # san cat sau 24 gio
                            break
                finally:
                    pt.cancel()
            if not refused:
                _status(ws="mất kết nối — nối lại")
        except Exception as e:
            _status(ws=f"lỗi: {str(e)[:160]}")
        # Luon nghi truoc khi noi lai, ke ca khi san dong ket noi binh thuong
        await asyncio.sleep(back)
        back = min(back * 2, 1800)


async def poll_loop(cx):
    while True:
        try:
            for cat in (161, 49):
                r = await cx.get(DL.URL, params={"type": 1, "catalogId": cat,
                                                 "pageNo": 1, "pageSize": 5},
                                 headers=DL.UA)
                if r.status_code == 429:
                    _status(poll="429 — tạm nghỉ")
                    await asyncio.sleep(120)
                    break
                r.raise_for_status()
                for a in r.json()["data"]["catalogs"][0]["articles"]:
                    t_pub = int(a["releaseDate"])
                    if now_ms() - t_pub > 10 * 60_000:
                        continue                  # bai cu: khong mo lenh, khong phai mau do tre
                    body = ""
                    if DL.parse(a["title"]) == [("F*", "")]:
                        d = await cx.get(DL.DETAIL, params={"articleCode": a["code"]}, headers=DL.UA)
                        body = (d.json().get("data") or {}).get("body") or ""
                    await handle(cx, cat, a["title"], body, t_pub, now_ms(), "poll")
                await asyncio.sleep(1.5)
            _status(poll_ok=int(now_ms()))
        except Exception as e:
            _status(poll=f"lỗi: {str(e)[:160]}")
        await asyncio.sleep(30)


def _open_rows() -> list:
    cx = db.connect()
    try:
        return [dict(r) for r in cx.execute("SELECT * FROM news_paper WHERE open=1")]
    finally:
        cx.close()


def _close(r, px, why):
    bps = (r["entry_px"] - px) / r["entry_px"] * 1e4 - COST
    with db.tx() as c:
        c.execute("UPDATE news_paper SET open=0, t_exit=?, exit_px=?, why=?, bps=?, usd=?"
                  " WHERE id=?", (int(now_ms()), px, why, bps, CFG.news_paper_usd * bps / 1e4, r["id"]))
    db.log("info", f"TIN {r['kind']} {r['symbol']}: sổ giấy đóng {px:g} ({why}) · {bps:+.0f} bps")


async def watch_loop(cx):
    """Moi giay: doi stop hoa von (S), dong sau 24 gio."""
    while True:
        rows = _open_rows()
        if not rows:
            await asyncio.sleep(5)
            continue
        try:
            book = {b["symbol"]: b for b in await _book(cx)}
        except Exception:
            await asyncio.sleep(3)
            continue
        t = now_ms()
        for r in rows:
            b = book.get(r["symbol"])
            if b is None:
                if t - r["t_entry"] > 60_000:
                    _close(r, r["last_px"] or r["entry_px"], "perp biến mất — đóng ở giá cuối đã thấy")
                continue
            ask = float(b["askPrice"])
            if ask <= 0:
                continue
            low = min(r["low"], ask)
            armed, stop = r["armed"], r["stop"]
            if r["kind"] == "S" and not armed and low <= r["entry_px"] * (1 - G_ARM):
                armed, stop = 1, r["entry_px"]
                db.log("info", f"TIN S {r['symbol']}: lời 15% — dời stop về giá vào {stop:g}")
            if armed and stop and ask >= stop:
                _close(r, ask, "hoà vốn")
                continue
            if t - r["t_entry"] >= HOLD:
                _close(r, ask, "hết 24 giờ")
                continue
            with db.tx() as c:
                c.execute("UPDATE news_paper SET low=?, armed=?, stop=?, last_px=? WHERE id=?",
                          (low, armed, stop, ask, r["id"]))
        await asyncio.sleep(1)


async def _sync_clock(cx):
    try:
        a = time.time() * 1000
        r = await cx.get(f"{CFG.public_rest}/fapi/v1/time")
        b = time.time() * 1000
        _OFF[0] = r.json()["serverTime"] - (a + b) / 2
        _status(clock_off_ms=round(_OFF[0]), clock_rtt_ms=round(b - a))
    except Exception:
        pass


async def clock_loop(cx):
    while True:
        await asyncio.sleep(600)
        await _sync_clock(cx)


async def main() -> None:
    _LOCK[0] = asyncio.Lock()
    async with httpx.AsyncClient(timeout=10) as cx:
        await _sync_clock(cx)
        await asyncio.gather(clock_loop(cx), ws_loop(cx), poll_loop(cx), watch_loop(cx))


def run() -> None:
    """Chay trong luong rieng, vong lap asyncio rieng. Loi khong lam sap app."""
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            db.log("error", f"sổ giấy theo tin dừng: {e} — chạy lại sau 30 s")
            time.sleep(30)


def summary() -> dict:
    cx = db.connect()
    try:
        lat = [r[0] for r in cx.execute(
            "SELECT (t_recv - t_pub) / 1000.0 FROM news WHERE src='ws' AND t_recv - t_pub < 600000"
            " ORDER BY t_recv DESC LIMIT 500")]
        lat_p = [r[0] for r in cx.execute(
            "SELECT (t_recv - t_pub) / 1000.0 FROM news WHERE src='poll' ORDER BY t_recv DESC LIMIT 500")]
        paper = [dict(r) for r in cx.execute("SELECT * FROM news_paper ORDER BY t_pub DESC LIMIT 100")]
        news = [dict(r) for r in cx.execute("SELECT * FROM news ORDER BY t_pub DESC LIMIT 60")]
    finally:
        cx.close()

    def q(v, p):
        v = sorted(v)
        return v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] if v else None
    return {"status": db.kv_get("news_status", {}) or {},
            "latency": {"ws": {"n": len(lat), "p50": q(lat, .5), "p90": q(lat, .9), "min": q(lat, 0)},
                        "poll": {"n": len(lat_p), "p50": q(lat_p, .5), "p90": q(lat_p, .9)}},
            "paper": paper, "news": news, "usd": CFG.news_paper_usd}
