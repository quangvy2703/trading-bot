"""Thong bao huy niem yet cua Binance → khong MUA ma do bang chien luoc nao.

Nguon: API CMS cong khai cua Binance, muc «Delisting» (catalogId 161). Gio
dang tinh den mili-giay. Hai loai thong bao duoc tinh (chep NGUYEN luat tach
cua scripts/delist_fetch.py):
  S : "Binance Will Delist X, Y on <ngay>"            — go ma khoi spot
  F : "Binance Futures Will Delist XUSDT ... Perpetual" — go chinh perp; tieu
      de "Multiple ..." thi doc ma trong than bai
Bo qua: go cap giao dich («Notice of Removal of ... Trading Pairs»), margin,
vay, staking, Alpha, quyen chon, token don bay, hoan go.

Luat: ma <base>USDT co thong bao trong `ban_days` ngay truoc luot chay thi
RSI(2) khong mo lop moi va dong luong khong mo chan MUA. Vi the dang giu
KHONG bi dong som; chan BAN cua dong luong khong bi chan. Xem
docs/huy-niem-yet.md.
"""
from __future__ import annotations

import re
import time

from . import db
from .binance import DAY

URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
DETAIL = "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query"
UA = {"user-agent": "Mozilla/5.0"}
STOP = {"USDT", "USDC", "BUSD", "AND", "ON", "THE", "WILL", "DELIST", "BINANCE",
        "FUTURES", "PERPETUAL", "CONTRACT", "CONTRACTS"}
# tieu de khong phai go ma: margin/vay/staking/Alpha/quyen chon/token don bay
SKIP = re.compile(r"(?i)^binance (margin|vip|staking|alpha|loans?|earn|to delist)|options|"
                  r"leveraged token|rebrand|postpone|loanable")


def perp_syms(text: str) -> list[str]:
    """Base cua moi hop dong <base>USDT nhac toi (bo hop dong COIN-M / USDC)."""
    return sorted(set(re.findall(r"\b([0-9A-Z]{1,20})USDT\b", text)))


def parse(title: str) -> list[tuple[str, str]]:
    """[(loai, base)] tu tieu de. ("F*", "") = go perp nhung tieu de khong ghi ma
    ("Multiple ... Perpetual Contracts") — nguoi goi doc than bai bang perp_syms."""
    t = title.strip()
    tl = t.lower()
    if SKIP.search(t):
        return []
    if tl.startswith("binance futures will delist"):
        if "COIN-M" in t and "USDⓈ-M" not in t:
            return []                          # chi hop dong ky quy bang coin
        if "BUSD" in t and "USDT" not in t:
            return []                          # dot go hop dong BUSD 2023, khong go ma
        b = perp_syms(t)
        if not b and "usdt-margined" in tl:
            # mau 2022: "Binance Futures Will Delist TLM and ICP USDT-Margined Contracts"
            b = sorted({x for x in re.findall(r"\b[0-9A-Z]{1,15}\b", t)
                        if x not in STOP | {"USDT"} and not x.endswith("BUSD")})
        return [("F", x) for x in b] if b else [("F*", "")]
    # spot: phai co ngay go "on YYYY-MM-DD" — loai cac thong bao go cap margin / Earn
    m = re.search(r"(?i)\bwill delist\s+(.+?)\s+on\s+\d{4}-\d\d-\d\d", t)
    if m and tl.startswith("binance"):
        return [("S", x) for x in re.findall(r"\b[0-9A-Z]{1,15}\b", m.group(1)) if x not in STOP]
    return []


def _get(cx, url: str, **params):
    """API nay tra 429 khi doc dồn: nghi 10 / 30 / 60 giay roi thu lai."""
    for wait in (10, 30, 60, None):
        r = cx.get(url, params=params)
        if r.status_code != 429 or wait is None:
            r.raise_for_status()
            return r
        time.sleep(wait)


def refresh(pages: int = 2) -> int:
    """Doc `pages` trang moi nhat (20 bai/trang). Lan dau: pages lon de lay du."""
    import httpx
    rows = []
    with httpx.Client(headers=UA, timeout=20) as cx:
        for p in range(1, pages + 1):
            r = _get(cx, URL, type=1, catalogId=161, pageNo=p, pageSize=20)
            c = r.json()["data"]["catalogs"][0]
            a = c["articles"]
            for x in a:
                ev = parse(x["title"])
                if ev == [("F*", "")]:
                    # "Multiple ... Perpetual Contracts": ma nam trong than bai
                    time.sleep(1.5)
                    d = _get(cx, DETAIL, articleCode=x["code"])
                    ev = [("F", b) for b in perp_syms(d.json()["data"].get("body") or "")]
                for kind, base in ev:
                    rows.append((base + "USDT", kind, int(x["releaseDate"]), x["title"]))
            if not a or p * 20 >= int(c.get("total") or 0):
                break
            time.sleep(1.5)                 # API nay chan 429 rat nhanh
    if rows:
        with db.tx() as cx2:
            # Giu thong bao DAU TIEN cua moi (ma, loai) — trang moi nhat doc truoc
            cx2.executemany("INSERT INTO delist(symbol, kind, ts, title) VALUES(?,?,?,?)"
                            " ON CONFLICT(symbol, kind) DO UPDATE SET ts = excluded.ts,"
                            " title = excluded.title WHERE excluded.ts < delist.ts", rows)
    return len(rows)


def notices() -> dict:
    """{ma: [ts, ...]} — moi thong bao go ma da biet."""
    cx = db.connect()
    try:
        out: dict = {}
        for s, ts in cx.execute("SELECT symbol, ts FROM delist ORDER BY ts"):
            out.setdefault(s, []).append(int(ts))
        return out
    finally:
        cx.close()


def banned(N: dict, t_run: int, days: int) -> dict:
    """{ma: ts thong bao} cho ma co thong bao trong (t_run − days, t_run]."""
    if days <= 0:
        return {}
    lo = t_run - days * DAY
    return {s: max(x for x in v if lo < x <= t_run) for s, v in N.items()
            if any(lo < x <= t_run for x in v)}
