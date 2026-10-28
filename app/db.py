"""Kho trang thai: SQLite + WAL. Mot tien trinh ghi duy nhat."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from .config import CFG

_LOCK = threading.Lock()

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=10000;

CREATE TABLE IF NOT EXISTS bars(
  symbol TEXT, ts INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL,
  PRIMARY KEY(symbol, ts)) WITHOUT ROWID;

-- Nen 1H chi de dung volume profile (cat lo HVN cua RSI(2)) — chi giu
-- top thanh khoan, khong phai ca vu tru. Xem app/volprofile.py.
CREATE TABLE IF NOT EXISTS bars1h(
  symbol TEXT, ts INTEGER, h REAL, l REAL, c REAL, v REAL,
  PRIMARY KEY(symbol, ts)) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS funding(
  symbol TEXT, ts INTEGER, rate REAL,
  PRIMARY KEY(symbol, ts)) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);

CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER, bar_ts INTEGER, mode TEXT, status TEXT, detail TEXT);

CREATE TABLE IF NOT EXISTS positions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  strategy TEXT, sleeve INTEGER, symbol TEXT, side INTEGER,
  qty REAL, weight REAL, entry_px REAL, entry_ts INTEGER,
  stop REAL, mode TEXT, open INTEGER DEFAULT 1,
  exit_px REAL, exit_ts INTEGER, exit_why TEXT, pnl_bps REAL);
CREATE INDEX IF NOT EXISTS ix_pos_open ON positions(mode, open);

CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER, ts INTEGER, strategy TEXT, sleeve INTEGER,
  symbol TEXT, action TEXT, side TEXT, qty REAL, notional REAL,
  mode TEXT, status TEXT, px REAL, resp TEXT);
CREATE INDEX IF NOT EXISTS ix_ord_run ON orders(run_id);

CREATE TABLE IF NOT EXISTS equity(
  ts INTEGER, mode TEXT, value REAL, PRIMARY KEY(ts, mode)) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER, level TEXT, msg TEXT);
CREATE INDEX IF NOT EXISTS ix_ev_ts ON events(ts DESC);
"""


def _migrate(cx) -> None:
    """Them cot moi cho so sach theo don vi R. Chay duoc nhieu lan.

    Ban cu luu `weight` = ty le von; ban moi luu `notional` = gia tri hop
    dong USD. Giu lai cot cu de vi the dang mo truoc khi doi van doc duoc.
    """
    for tbl, col, typ in (("positions", "notional", "REAL"),
                          ("positions", "r_usd", "REAL"),
                          ("runs", "n_open", "INTEGER"),
                          ("runs", "gross", "REAL")):
        cols = {r[1] for r in cx.execute(f"PRAGMA table_info({tbl})")}
        if col not in cols:
            cx.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")


def connect() -> sqlite3.Connection:
    Path(CFG.db_path).parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(CFG.db_path, timeout=15, check_same_thread=False)
    cx.row_factory = sqlite3.Row
    return cx


@contextmanager
def tx():
    """Mot ghi tai mot thoi diem: SQLite chi co mot nguoi ghi."""
    with _LOCK:
        cx = connect()
        try:
            yield cx
            cx.commit()
        except Exception:
            cx.rollback()
            raise
        finally:
            cx.close()


def init() -> None:
    with tx() as cx:
        cx.executescript(SCHEMA)
        _migrate(cx)


def kv_get(k: str, default=None):
    cx = connect()
    try:
        r = cx.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return json.loads(r["v"]) if r else default
    finally:
        cx.close()


def kv_set(k: str, v) -> None:
    with tx() as cx:
        cx.execute("INSERT INTO kv(k,v) VALUES(?,?) "
                   "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                   (k, json.dumps(v)))


def log(level: str, msg: str) -> None:
    with tx() as cx:
        cx.execute("INSERT INTO events(ts,level,msg) VALUES(?,?,?)",
                   (int(time.time() * 1000), level, msg))
