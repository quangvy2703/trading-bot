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


# The Monitoring (muc 49, tu 2023-10): canh bao truoc khi go. ~80% ma bi gan
# the ve sau bi go khoi spot. Them va bo the thuong nam chung mot bai:
#   "Binance Will Extend the Monitoring Tag to Include X & Y, Remove the
#    Monitoring Tag for Z, and Remove the Seed Tag for ... on 2026-03-06"
MON_ADD = re.compile(r"(?i)monitoring tag to (?:include\s+)?(.+?)"
                     r"(?:,?\s+(?:and\s+)?remove\b|\s+on\s+\d{4}-|$)")
MON_DEL = re.compile(r"(?i)remove the monitoring tag (?:for|from)\s+(.+?)"
                     r"(?:,?\s+(?:and\s+)?(?:the\s+)?(?:remove|extend|add|seed)\b|\s+on\s+\d{4}-|$)")
MON_START = 1688169600000                 # 2023-07-01: the ra doi 26/07/2023


def _bases(s: str) -> list[str]:
    s = re.sub(r"\(.*?\)", " ", s)
    return [x for x in re.findall(r"\b[0-9A-Z]{1,15}\b", s) if x not in STOP]


def parse_monitor(title: str) -> list[tuple[str, str]]:
    """[("add"|"remove", base)] tu tieu de bai muc 49."""
    out = []
    m = MON_ADD.search(title)
    if m and "seed tag" not in m.group(1).lower():
        out += [("add", b) for b in _bases(m.group(1))]
    for m in MON_DEL.finditer(title):
        out += [("remove", b) for b in _bases(m.group(1))]
    return out


def store_monitor(title: str, ts: int, code: str | None = None) -> int:
    rows = [(b + "USDT", int(ts), act, title, code) for act, b in parse_monitor(title)]
    if rows:
        with db.tx() as cx:
            cx.executemany("INSERT INTO monitor(symbol, ts, action, title, code) VALUES(?,?,?,?,?)"
                           " ON CONFLICT(symbol, ts, action) DO UPDATE SET"
                           " code = COALESCE(monitor.code, excluded.code)", rows)
    return len(rows)


def refresh_monitor(pages: int = 2) -> int:
    """Doc muc 49 tu moi nhat lui ve 2023-07 (hoac `pages` trang)."""
    import httpx
    n = 0
    with httpx.Client(headers=UA, timeout=20) as cx:
        for p in range(1, pages + 1):
            c = _get(cx, URL, type=1, catalogId=49, pageNo=p, pageSize=20).json()["data"]["catalogs"][0]
            a = c["articles"]
            for x in a:
                n += store_monitor(x["title"], int(x["releaseDate"]), x["code"])
            if not a or int(a[-1]["releaseDate"]) < MON_START or p * 20 >= int(c.get("total") or 0):
                break
            time.sleep(1.5)
    return n


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
                    rows.append((base + "USDT", kind, int(x["releaseDate"]), x["title"], x["code"]))
            if not a or p * 20 >= int(c.get("total") or 0):
                break
            time.sleep(1.5)                 # API nay chan 429 rat nhanh
    if rows:
        with db.tx() as cx2:
            # Giu thong bao DAU TIEN cua moi (ma, loai) — trang moi nhat doc truoc
            cx2.executemany(
                "INSERT INTO delist(symbol, kind, ts, title, code) VALUES(?,?,?,?,?)"
                " ON CONFLICT(symbol, kind) DO UPDATE SET"
                " title = CASE WHEN excluded.ts < delist.ts THEN excluded.title ELSE delist.title END,"
                " code = CASE WHEN excluded.ts < delist.ts OR delist.code IS NULL"
                "        THEN excluded.code ELSE delist.code END,"
                " ts = MIN(delist.ts, excluded.ts)", rows)
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


ANN = "https://www.binance.com/en/support/announcement/detail/"


def flags(ban_days: int, t_now: int) -> list[dict]:
    """Moi ma tung co co: tin go spot / go perp / the Monitoring, va trang thai."""
    cx = db.connect()
    try:
        D = [dict(r) for r in cx.execute("SELECT * FROM delist")]
        Mo = [dict(r) for r in cx.execute("SELECT * FROM monitor ORDER BY ts")]
        last = dict(cx.execute("SELECT symbol, MAX(ts) FROM bars GROUP BY symbol").fetchall())
        held = {r[0] for r in cx.execute("SELECT DISTINCT symbol FROM positions WHERE open=1")}
    finally:
        cx.close()
    out: dict = {}

    def row(s):
        return out.setdefault(s, {"symbol": s, "S": None, "F": None, "tag_add": None,
                                  "tag_remove": None, "links": []})
    for r in D:
        x = row(r["symbol"])
        x[r["kind"]] = r["ts"]
        x["links"].append({"kind": r["kind"], "ts": r["ts"], "title": r["title"],
                           "url": ANN + r["code"] if r.get("code") else None})
    for r in Mo:
        x = row(r["symbol"])
        if r["action"] == "add":
            x["tag_add"] = r["ts"]
        else:
            x["tag_remove"] = r["ts"]
        x["links"].append({"kind": "M" if r["action"] == "add" else "M−", "ts": r["ts"],
                           "title": r["title"], "url": ANN + r["code"] if r.get("code") else None})
    lo = t_now - ban_days * DAY
    for x in out.values():
        gone = max(x["S"] or 0, x["F"] or 0)
        x["tag_on"] = bool(x["tag_add"] and (x["tag_remove"] or 0) < x["tag_add"]
                           and (x["S"] or 0) < x["tag_add"])
        x["ban_until"] = (gone + ban_days * DAY) if ban_days > 0 and gone > lo else None
        lb = last.get(x["symbol"])
        x["perp"] = bool(lb and lb >= t_now - 3 * DAY)
        x["held"] = x["symbol"] in held
        x["last_ts"] = max(l["ts"] for l in x["links"])
        x["links"].sort(key=lambda l: l["ts"])
    return sorted(out.values(), key=lambda x: -x["last_ts"])


def seed_from_cache(path: str) -> tuple[int, int]:
    """Gieo bang delist + monitor tu file da tai san. Tra (so dong go, so dong the)."""
    import json
    from pathlib import Path
    d = Path(path)
    if not d.is_dir():
        return 0, 0
    bodies = json.loads((d / "bodies.json").read_text()) if (d / "bodies.json").exists() else {}
    rows, nm = [], 0
    for cat in (161, 49):
        f = d / f"{cat}.json"
        if not f.exists():
            continue
        for x in json.loads(f.read_text()):
            ev = parse(x["title"])
            if ev == [("F*", "")]:
                ev = [("F", b) for b in perp_syms(bodies.get(x["code"], ""))]
            rows += [(b + "USDT", k, int(x["ts"]), x["title"], x["code"]) for k, b in ev]
            if cat == 49 and x["ts"] >= MON_START:
                nm += store_monitor(x["title"], int(x["ts"]), x["code"])
    if rows:
        with db.tx() as cx:
            cx.executemany(
                "INSERT INTO delist(symbol, kind, ts, title, code) VALUES(?,?,?,?,?)"
                " ON CONFLICT(symbol, kind) DO UPDATE SET"
                " title = CASE WHEN excluded.ts < delist.ts THEN excluded.title ELSE delist.title END,"
                " code = CASE WHEN excluded.ts < delist.ts OR delist.code IS NULL"
                "        THEN excluded.code ELSE delist.code END,"
                " ts = MIN(delist.ts, excluded.ts)", rows)
    return len(rows), nm
