# Trade Explorer Webapp — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mot man hinh cuc bo de do tham so luat vao lenh: chon config, chay, xem tung lenh duoi dang the nho co 5 nen ke tiep, sua TP/SL truc tiep.

**Architecture:** Server Python cuc bo (`http.server`) goi thang cac ham numpy da kiem chung trong `scripts/backtest_taker_oi.py` — khong nhan ban logic sang JavaScript. Ket qua cache ra dia theo khoa bam tu config + `RULE_VERSION`. Frontend la HTML/JS thuan, khong framework, ve SVG bang tay giong `scripts/build_trading_data_ui.py`.

**Tech Stack:** Python 3.10+ (stdlib `http.server`, `numpy`), pytest 9 trong `.venv`, JavaScript thuan + `node:test` cho ham hinh hoc.

## Global Constraints

- **Khong nhan ban logic tin hieu.** Moi tinh toan goi `backtest_taker_oi.py`. Mot ban JavaScript song song se troi khoi no ma khong ai phat hien.
- **`RULE_VERSION = 5`** nam trong `scripts/webapp/rules.py`. Tang moi khi dinh nghia tin hieu doi. Khoa cache PHAI chua no.
- **Server chi bind `127.0.0.1`.** Mo ra mang la quyet dinh cua nguoi dung, khong phai mac dinh.
- **Dinh danh (ham, bien, test) bang tieng Anh. Comment va chuoi hien thi bang tieng Viet.**
- **Phi taker 0,05% moi chieu** (`backtest_taker_oi.FEE = 0.0005`), tran giu lenh 48h (`CAP_H = 48`).
- **Vao lenh o gia MO cua nen KE TIEP.** SL o day nen (mua) / dinh nen (ban). TP = 2R.
- Chay test bang `.venv/bin/python -m pytest`, khong phai `python3 -m pytest` (pytest chi co trong venv).
- Moi commit ket thuc bang dong `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## Luat ma app tinh (RULE_VERSION 5)

```
loc chung   volume >= trung binh n nen TRUOC do
MUA         taker buy > 60% · close > open · rau tren <= wick x bien do nen
            · OI tang lien tuc n phien · high >= max(high cua n-1 nen truoc)
BAN         taker buy < 40% · close < open · rau duoi <= wick x bien do nen
            · OI tang lien tuc n phien · low <= min(low cua n-1 nen truoc)
```

Mot tham so `n` chi phoi ba cho: chu ky MA volume, so phien OI tang lien tuc, be rong cua so cuc tri. Dieu kien OI **khong phan chieu** — ca hai ben deu doi OI tang.

## File Structure

| tep | trach nhiem |
|---|---|
| `scripts/webapp/__init__.py` | rong, de `import webapp.x` chay duoc |
| `scripts/webapp/rules.py` | `RuleConfig`, `RULE_VERSION`, `evaluate()` -> mat na + pheu |
| `scripts/webapp/store.py` | khoa cache, doc/ghi `runs/` va `edits/` |
| `scripts/webapp/compute.py` | `load()`, `run()`, `replay_one()` |
| `scripts/webapp/jobs.py` | dang ky job, tien do, huy |
| `scripts/webapp/serve.py` | dinh tuyen HTTP, SSE, phuc vu tinh |
| `scripts/webapp/static/index.html` | khung trang |
| `scripts/webapp/static/app.css` | kieu dang |
| `scripts/webapp/static/card.js` | ve MOT the + bat tay cam keo |
| `scripts/webapp/static/app.js` | thanh config, luong chay, luoi, lazy-load |
| `tests/test_webapp_rules.py` | mat na va pheu tren nen tong hop |
| `tests/test_webapp_store.py` | on dinh khoa, RULE_VERSION vo hieu hoa cache |
| `tests/test_webapp_compute.py` | golden vs `bt_rule_extreme.py`, replay khu hoi |
| `tests/test_webapp_api.py` | server that tren cong tam |
| `tests/test_card.mjs` | hinh hoc the, chay bang `node --test` |

---

### Task 1: `rules.py` — cau hinh, mat na tin hieu, pheu dieu kien

**Files:**
- Create: `scripts/webapp/__init__.py`
- Create: `scripts/webapp/rules.py`
- Create: `tests/test_webapp_rules.py`
- Modify: `pyproject.toml` (them `"scripts"` vao `pythonpath`)

**Interfaces:**
- Consumes: `backtest_taker_oi.signals(bars, tol, oi_ma, buy_th, sell_th, trend_n)`, `bt_rule_extreme.oi_streak(oi, n)`, `bt_rule_extreme.rolling_extreme(a, n, how)`
- Produces:
  - `RULE_VERSION: int = 5`
  - `RuleConfig(symbol: str, tf: str, n: int, wick: float, days: int, buy_th: float = 0.60, sell_th: float = 0.40)` — frozen dataclass, co `.as_dict() -> dict`
  - `evaluate(bars: dict, cfg: RuleConfig) -> dict` tra `{"long": np.ndarray[bool], "short": np.ndarray[bool], "funnel": {"long": list[dict], "short": list[dict]}}`; moi phan tu pheu la `{"name": str, "left": int, "pct": float | None}` (`pct` la `None` o dong dau)

- [ ] **Step 1: Them `scripts` vao pythonpath cua pytest**

Trong `pyproject.toml`, doi:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```
thanh:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src", "scripts"]
```

- [ ] **Step 2: Viet test that bai**

Tao `tests/test_webapp_rules.py`:
```python
"""Mat na tin hieu tren nen TONG HOP -- moi dieu kien duoc bat mot cach co chu y.

Dung nen tong hop chu khong dung du lieu that: o day can biet CHINH XAC nen nao
phai do va vi sao. Doi chieu voi du lieu that nam o test_webapp_compute.py.
"""
import numpy as np
import pytest

from webapp.rules import RULE_VERSION, RuleConfig, evaluate


def make_bars(n_bars: int = 40) -> dict:
    """Nen di ngang, volume deu, OI phang. Test tu dung cai no can len tren."""
    t = np.arange(n_bars, dtype=np.int64) * 3_600_000
    o = np.full(n_bars, 100.0)
    c = np.full(n_bars, 100.0)
    h = np.full(n_bars, 101.0)
    lo = np.full(n_bars, 99.0)
    v = np.full(n_bars, 10.0)
    buy = np.full(n_bars, 5.0)
    sell = np.full(n_bars, 5.0)
    oi = np.full(n_bars, 1000.0)
    return {"t": t, "o": o, "c": c, "h": h, "l": lo, "v": v,
            "buy": buy, "sell": sell, "oi": oi,
            "i0": np.arange(n_bars), "i1": np.arange(1, n_bars + 1)}


def test_rule_version_is_five():
    assert RULE_VERSION == 5


def test_no_signal_on_flat_bars():
    bars = make_bars()
    out = evaluate(bars, RuleConfig(n=5, wick=0.10))
    assert not out["long"].any()
    assert not out["short"].any()


def test_long_fires_when_every_condition_holds():
    bars = make_bars()
    i = 20
    bars["oi"][:] = np.arange(len(bars["t"]), dtype=float)   # OI tang moi nen
    bars["v"][i] = 100.0                                     # vol vuot MA5
    bars["buy"][i], bars["sell"][i] = 9.0, 1.0               # taker 90%
    bars["o"][i], bars["c"][i] = 100.0, 105.0                # nen xanh
    bars["h"][i], bars["l"][i] = 105.0, 99.0                 # khong rau tren
    out = evaluate(bars, RuleConfig(n=5, wick=0.10))
    assert out["long"][i]
    assert not out["short"].any()


def test_upper_wick_blocks_long():
    bars = make_bars()
    i = 20
    bars["oi"][:] = np.arange(len(bars["t"]), dtype=float)
    bars["v"][i] = 100.0
    bars["buy"][i], bars["sell"][i] = 9.0, 1.0
    bars["o"][i], bars["c"][i] = 100.0, 105.0
    bars["h"][i], bars["l"][i] = 110.0, 99.0    # rau tren 5/11 = 45% bien do
    out = evaluate(bars, RuleConfig(n=5, wick=0.10))
    assert not out["long"][i]


def test_oi_must_rise_every_one_of_n_bars():
    bars = make_bars()
    i = 20
    bars["oi"][:] = np.arange(len(bars["t"]), dtype=float)
    bars["oi"][i - 2] = bars["oi"][i - 3]        # mot phien khong tang -> hong chuoi
    bars["v"][i] = 100.0
    bars["buy"][i], bars["sell"][i] = 9.0, 1.0
    bars["o"][i], bars["c"][i] = 100.0, 105.0
    bars["h"][i], bars["l"][i] = 105.0, 99.0
    out = evaluate(bars, RuleConfig(n=5, wick=0.10))
    assert not out["long"][i]


def test_short_needs_oi_rising_too():
    """Dieu kien OI KHONG phan chieu: lenh ban cung doi OI tang."""
    bars = make_bars()
    i = 20
    bars["oi"][:] = np.arange(len(bars["t"]), 0, -1, dtype=float)   # OI GIAM
    bars["v"][i] = 100.0
    bars["buy"][i], bars["sell"][i] = 1.0, 9.0
    bars["o"][i], bars["c"][i] = 105.0, 100.0
    bars["h"][i], bars["l"][i] = 106.0, 100.0
    out = evaluate(bars, RuleConfig(n=5, wick=0.10))
    assert not out["short"][i]


def test_funnel_is_monotonic_and_starts_at_bar_count():
    bars = make_bars()
    out = evaluate(bars, RuleConfig(n=5, wick=0.10))
    for side in ("long", "short"):
        steps = out["funnel"][side]
        assert steps[0]["left"] == len(bars["t"])
        assert steps[0]["pct"] is None
        lefts = [s["left"] for s in steps]
        assert lefts == sorted(lefts, reverse=True), "pheu phai giam don dieu"
        assert steps[-1]["left"] == int(out[side].sum())


def test_config_as_dict_round_trips():
    cfg = RuleConfig(symbol="ETHUSDT", tf="4h", n=7, wick=0.05, days=365)
    assert RuleConfig(**cfg.as_dict()) == cfg
```

- [ ] **Step 3: Chay test de chac chan no that bai**

Run: `.venv/bin/python -m pytest tests/test_webapp_rules.py -q`
Expected: FAIL voi `ModuleNotFoundError: No module named 'webapp'`

- [ ] **Step 4: Viet `rules.py`**

Tao `scripts/webapp/__init__.py` rong, va `scripts/webapp/rules.py`:
```python
"""Config -> mat na tin hieu long/short, kem pheu dieu kien.

Module nay KHONG tu tinh gi ca ngoai viec ghep cac mat na da co trong
`backtest_taker_oi.signals` va `bt_rule_extreme`. Moi thay doi dinh nghia tin
hieu phai di kem tang RULE_VERSION, neu khong cache cu se duoc phuc vu cho
mot luat moi va khong ai phat hien ra.
"""
from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import backtest_taker_oi as T      # noqa: E402
import bt_rule_extreme as E        # noqa: E402

RULE_VERSION = 5


@dataclass(frozen=True)
class RuleConfig:
    symbol: str = "BTCUSDT"
    tf: str = "1h"
    n: int = 5
    wick: float = 0.10
    days: int = 365
    buy_th: float = 0.60
    sell_th: float = 0.40

    def as_dict(self) -> dict:
        return asdict(self)


def volume_ok(v: np.ndarray, n: int) -> np.ndarray:
    """volume >= trung binh n nen TRUOC do (khong ke chinh no)."""
    ma = np.full(len(v), np.nan)
    cs = np.concatenate(([0.0], np.cumsum(v)))
    ma[n:] = (cs[n:-1] - cs[: -n - 1]) / n
    return v >= ma


def evaluate(bars: dict, cfg: RuleConfig) -> dict:
    n = cfg.n
    sig = T.signals(bars, cfg.wick, 20, cfg.buy_th, cfg.sell_th, trend_n=n)
    have = np.isfinite(bars["buy"]) & np.isfinite(bars["oi"])
    vol = volume_ok(bars["v"], n)
    streak = E.oi_streak(bars["oi"], n)
    top = E.rolling_extreme(bars["h"], n, "max")
    bot = E.rolling_extreme(bars["l"], n, "min")
    green, red = bars["c"] > bars["o"], bars["c"] < bars["o"]

    ladders = {
        "long": [("du taker + OI", have), ("vol >= MA(n)", vol),
                 (f"taker > {cfg.buy_th:.0%}", sig["share"] > cfg.buy_th),
                 ("close > open", green),
                 (f"rau tren <= {cfg.wick:.0%}", sig["no_up"]),
                 ("OI tang lien tuc n", streak),
                 ("dinh cuc tri n", top)],
        "short": [("du taker + OI", have), ("vol >= MA(n)", vol),
                  (f"taker < {cfg.sell_th:.0%}", sig["share"] < cfg.sell_th),
                  ("close < open", red),
                  (f"rau duoi <= {cfg.wick:.0%}", sig["no_dn"]),
                  ("OI tang lien tuc n", streak),
                  ("day cuc tri n", bot)],
    }

    out: dict = {"funnel": {}}
    total = len(bars["t"])
    for side, ladder in ladders.items():
        mask = np.ones(total, bool)
        steps = [{"name": "tong so nen", "left": total, "pct": None}]
        prev = total
        for name, cond in ladder:
            mask = mask & cond
            left = int(mask.sum())
            steps.append({"name": name, "left": left,
                          "pct": (left / prev) if prev else 0.0})
            prev = left
        out[side] = mask
        out["funnel"][side] = steps
    return out
```

- [ ] **Step 5: Chay test de chac chan no dat**

Run: `.venv/bin/python -m pytest tests/test_webapp_rules.py -q`
Expected: PASS, 8 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml scripts/webapp/__init__.py scripts/webapp/rules.py tests/test_webapp_rules.py
git commit -m "feat(webapp): rule config, signal masks, condition funnel

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `store.py` — khoa cache va luu tru

**Files:**
- Create: `scripts/webapp/store.py`
- Create: `tests/test_webapp_store.py`

**Interfaces:**
- Consumes: `webapp.rules.RuleConfig`, `webapp.rules.RULE_VERSION`
- Produces:
  - `cache_key(cfg: RuleConfig) -> str` — 16 ky tu hex
  - `Store(root: Path)` voi `read_run(key) -> dict | None`, `write_run(key, payload: dict) -> None`, `read_edits(key) -> dict`, `write_edit(key, idx: int, edit: dict) -> None`, `clear_edits(key) -> None`
  - Duong dan: `root/runs/<key>.json`, `root/edits/<key>.json`

- [ ] **Step 1: Viet test that bai**

Tao `tests/test_webapp_store.py`:
```python
import json

import pytest

from webapp import rules
from webapp.rules import RuleConfig
from webapp.store import Store, cache_key


def test_same_config_same_key():
    a = RuleConfig(symbol="BTCUSDT", tf="1h", n=5, wick=0.10, days=365)
    b = RuleConfig(symbol="BTCUSDT", tf="1h", n=5, wick=0.10, days=365)
    assert cache_key(a) == cache_key(b)


@pytest.mark.parametrize("field,value", [
    ("symbol", "ETHUSDT"), ("tf", "4h"), ("n", 7),
    ("wick", 0.05), ("days", 1095), ("buy_th", 0.65), ("sell_th", 0.35),
])
def test_every_config_field_changes_the_key(field, value):
    base = RuleConfig()
    other = RuleConfig(**{**base.as_dict(), field: value})
    assert cache_key(base) != cache_key(other), f"{field} khong doi khoa"


def test_rule_version_changes_the_key(monkeypatch):
    """Thieu rang buoc nay thi sua luat xong cache cu van duoc phuc vu."""
    cfg = RuleConfig()
    before = cache_key(cfg)
    monkeypatch.setattr(rules, "RULE_VERSION", rules.RULE_VERSION + 1)
    assert cache_key(cfg) != before


def test_run_round_trip(tmp_path):
    s = Store(tmp_path)
    assert s.read_run("abc") is None
    s.write_run("abc", {"trades": [1, 2, 3]})
    assert s.read_run("abc") == {"trades": [1, 2, 3]}
    assert (tmp_path / "runs" / "abc.json").exists()


def test_edits_round_trip_and_clear(tmp_path):
    s = Store(tmp_path)
    assert s.read_edits("abc") == {}
    s.write_edit("abc", 3, {"tp": 101.0, "sl": 99.0})
    s.write_edit("abc", 7, {"tp": 111.0, "sl": 98.0})
    assert s.read_edits("abc") == {"3": {"tp": 101.0, "sl": 99.0},
                                   "7": {"tp": 111.0, "sl": 98.0}}
    s.clear_edits("abc")
    assert s.read_edits("abc") == {}


def test_write_run_is_atomic(tmp_path):
    """Ghi truc tiep vao dich thi mot lan huy giua chung se de lai JSON cut,
    va lan chay sau se doc phai rac ma tuong la cache hop le."""
    s = Store(tmp_path)
    s.write_run("abc", {"a": 1})
    leftovers = list((tmp_path / "runs").glob("*.tmp"))
    assert leftovers == []
    assert json.loads((tmp_path / "runs" / "abc.json").read_text()) == {"a": 1}
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `.venv/bin/python -m pytest tests/test_webapp_store.py -q`
Expected: FAIL voi `ModuleNotFoundError: No module named 'webapp.store'`

- [ ] **Step 3: Viet `store.py`**

```python
"""Cache ra dia: ket qua chay va cac lan sua TP/SL bang tay.

Khoa PHAI chua RULE_VERSION. Khong co no, sua dinh nghia tin hieu xong thi
cache cu van khop khoa va duoc phuc vu -- nguoi dung nhin so cu tuong la so moi.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from . import rules
from .rules import RuleConfig


def cache_key(cfg: RuleConfig) -> str:
    d = cfg.as_dict()
    parts = "|".join(f"{k}={d[k]!r}" for k in sorted(d))
    # doc RULE_VERSION qua module chu khong import truc tiep, de test co the
    # thay doi no bang monkeypatch
    parts += f"|rule={rules.RULE_VERSION}"
    return hashlib.sha1(parts.encode()).hexdigest()[:16]


class Store:
    def __init__(self, root: Path):
        self.runs = Path(root) / "runs"
        self.edits = Path(root) / "edits"
        self.runs.mkdir(parents=True, exist_ok=True)
        self.edits.mkdir(parents=True, exist_ok=True)

    def _read(self, path: Path):
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            path.unlink()          # rac tu mot lan ghi do dang -> coi nhu chua co
            return None

    def _write(self, path: Path, payload) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, path)      # doi ten la nguyen tu tren cung mot filesystem

    def read_run(self, key: str):
        return self._read(self.runs / f"{key}.json")

    def write_run(self, key: str, payload: dict) -> None:
        self._write(self.runs / f"{key}.json", payload)

    def read_edits(self, key: str) -> dict:
        return self._read(self.edits / f"{key}.json") or {}

    def write_edit(self, key: str, idx: int, edit: dict) -> None:
        cur = self.read_edits(key)
        cur[str(idx)] = edit
        self._write(self.edits / f"{key}.json", cur)

    def clear_edits(self, key: str) -> None:
        (self.edits / f"{key}.json").unlink(missing_ok=True)
```

- [ ] **Step 4: Chay test de chac chan no dat**

Run: `.venv/bin/python -m pytest tests/test_webapp_store.py -q`
Expected: PASS, 12 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/webapp/store.py tests/test_webapp_store.py
git commit -m "feat(webapp): disk cache keyed by config and rule version

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `compute.py` — chay mot config ra danh sach lenh

**Files:**
- Create: `scripts/webapp/compute.py`
- Create: `tests/test_webapp_compute.py`

**Interfaces:**
- Consumes: `webapp.rules.RuleConfig`, `webapp.rules.evaluate`, `backtest_taker_oi.dataset/to_tf/brackets`, `build_trading_data_ui.PERIOD_MS`
- Produces:
  - `load(cfg: RuleConfig, cache_root: Path, progress=None) -> tuple[dict, dict]` tra `(five, bars)`
  - `run(cfg: RuleConfig, cache_root: Path, progress=None) -> dict` tra
    `{"config": dict, "funnel": dict, "trades": list[dict], "summary": dict}`
  - Moi lenh: `{"i", "side", "t", "entry", "stop", "tp", "xt", "xp", "r", "bps", "hrs", "bars"}`, trong do `bars` la 6 phan tu `{"t","o","h","l","c","v"}` — nen tin hieu va 5 nen ke
  - `summary`: `{"n_long", "n_short", "win_rate", "gross_r", "net_bps"}`

- [ ] **Step 1: Viet test that bai**

Tao `tests/test_webapp_compute.py`:
```python
"""Doi chieu duong web voi duong Python da kiem chung.

Test golden o day la rang buoc quan trong nhat cua ca du an: thieu no thi con
so tren man hinh khong con doi chieu duoc voi bat ky ket qua nghien cuu nao.
"""
from pathlib import Path

import numpy as np
import pytest

from webapp.compute import load, run
from webapp.rules import RuleConfig

CACHE = Path("reports/.cache/metrics")
NPZ = CACHE / "BTCUSDT" / "BTCUSDT-2100d-5m.npz"
needs_data = pytest.mark.skipif(
    not NPZ.exists(), reason=f"chua co {NPZ}; chay scripts/backtest_taker_oi.py truoc")


@needs_data
def test_matches_bt_rule_extreme_for_n5():
    """Cung config phai ra cung so lenh voi scripts/bt_rule_extreme.py."""
    import sys
    sys.path.insert(0, "scripts")
    import backtest_taker_oi as T
    import bt_rule_extreme as E
    import build_trading_data_ui as B

    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=5, wick=0.10, days=2100)
    out = run(cfg, CACHE)

    five = T.dataset("BTCUSDT", 2100, CACHE / "BTCUSDT")
    bars = T.to_tf(five, B.PERIOD_MS["1h"])
    sig = T.signals(bars, 0.10, 20, 0.60, 0.40, trend_n=5)
    good = np.isfinite(bars["buy"]) & np.isfinite(bars["oi"])
    st = E.oi_streak(bars["oi"], 5)
    vol = E._volok(bars["v"], 5)
    ref_long = good & vol & (sig["share"] > .60) & (bars["c"] > bars["o"]) \
        & sig["no_up"] & st & E.rolling_extreme(bars["h"], 5, "max")
    L = T.brackets(bars, five, +1, T.CAP_H * 12)
    expected = int((ref_long & np.isfinite(L["r"])).sum())

    assert out["summary"]["n_long"] == expected


@needs_data
def test_every_trade_carries_six_bars_starting_at_the_signal_bar():
    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=3, wick=0.10, days=2100)
    out = run(cfg, CACHE)
    assert out["trades"], "n=3 phai co lenh"
    step = 3_600_000
    for tr in out["trades"]:
        assert len(tr["bars"]) == 6
        assert tr["bars"][0]["t"] == tr["t"] - step, "phan tu dau phai la nen TIN HIEU"
        gaps = [tr["bars"][k + 1]["t"] - tr["bars"][k]["t"] for k in range(5)]
        assert gaps == [step] * 5


@needs_data
def test_entry_is_the_open_of_the_bar_after_the_signal():
    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=3, wick=0.10, days=2100)
    out = run(cfg, CACHE)
    for tr in out["trades"][:20]:
        assert tr["entry"] == pytest.approx(tr["bars"][1]["o"])


@needs_data
def test_stop_sits_at_the_signal_bar_extreme():
    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=3, wick=0.10, days=2100)
    out = run(cfg, CACHE)
    for tr in out["trades"][:20]:
        sig_bar = tr["bars"][0]
        want = sig_bar["l"] if tr["side"] == "long" else sig_bar["h"]
        assert tr["stop"] == pytest.approx(want)


@needs_data
def test_take_profit_is_two_r():
    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=3, wick=0.10, days=2100)
    out = run(cfg, CACHE)
    for tr in out["trades"][:20]:
        sign = 1 if tr["side"] == "long" else -1
        r = (tr["entry"] - tr["stop"]) * sign
        assert tr["tp"] == pytest.approx(tr["entry"] + sign * 2 * r)


@needs_data
def test_funnel_last_step_equals_trade_count_per_side():
    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=3, wick=0.10, days=2100)
    out = run(cfg, CACHE)
    n_long = sum(1 for t in out["trades"] if t["side"] == "long")
    # pheu dem NEN thoa dieu kien; lenh co the it hon khi nen cuoi chuoi khong
    # con nen ke tiep de vao lenh, hoac khi R <= 0
    assert out["funnel"]["long"][-1]["left"] >= n_long
    assert out["funnel"]["long"][-1]["left"] - n_long <= 2


@needs_data
def test_progress_callback_is_called_with_monotonic_values():
    seen = []
    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=5, wick=0.10, days=2100)
    run(cfg, CACHE, progress=lambda ph, done, total, msg: seen.append((ph, done, total)))
    assert seen, "phai bao tien do it nhat mot lan"
    assert seen[-1][1] == seen[-1][2], "buoc cuoi phai la done == total"
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `.venv/bin/python -m pytest tests/test_webapp_compute.py -q`
Expected: FAIL voi `ModuleNotFoundError: No module named 'webapp.compute'`

- [ ] **Step 3: Viet `compute.py`**

```python
"""Config -> danh sach lenh, dung lai nguyen duong tinh cua backtest_taker_oi.

Moi lenh mang theo 6 nen cua chinh no (nen tin hieu + 5 nen ke). 400 lenh x 6
nen ~60 KB -- re hon mot lan goi API, va nho no ma the o frontend khong bao gio
phai cho mang.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import backtest_taker_oi as T          # noqa: E402
import build_trading_data_ui as B      # noqa: E402

from .rules import RuleConfig, evaluate   # noqa: E402

Progress = Callable[[str, int, int, str], None]
BARS_AFTER = 5


def load(cfg: RuleConfig, cache_root: Path, progress: Progress | None = None):
    """Tra (five, bars). Tai du lieu neu chua cache -- day la pha CHAM."""
    if progress:
        progress("fetch", 0, 1, f"nap {cfg.symbol} {cfg.days} ngay")
    five = T.dataset(cfg.symbol, cfg.days, Path(cache_root) / cfg.symbol)
    if progress:
        progress("fetch", 1, 1, "xong")
    return five, T.to_tf(five, B.PERIOD_MS[cfg.tf])


def _slice_bars(bars: dict, i: int) -> list[dict]:
    """Nen tin hieu i va 5 nen ke. Ngan lai o cuoi chuoi."""
    hi = min(i + 1 + BARS_AFTER, len(bars["t"]))
    return [{"t": int(bars["t"][k]), "o": float(bars["o"][k]), "h": float(bars["h"][k]),
             "l": float(bars["l"][k]), "c": float(bars["c"][k]), "v": float(bars["v"][k])}
            for k in range(i, hi)]


def run(cfg: RuleConfig, cache_root: Path, progress: Progress | None = None) -> dict:
    five, bars = load(cfg, cache_root, progress)
    if progress:
        progress("compute", 0, 1, "tinh tin hieu")

    ev = evaluate(bars, cfg)
    cap = T.CAP_H * 12
    L = T.brackets(bars, five, +1, cap)
    S = T.brackets(bars, five, -1, cap)

    trades: list[dict] = []
    for side, mask, bk in (("long", ev["long"], L), ("short", ev["short"], S)):
        for i in np.flatnonzero(mask & np.isfinite(bk["r"])):
            i = int(i)
            j = int(bk["exit_j"][i])
            trades.append({
                "side": side,
                "t": int(bars["t"][i + 1]),
                "entry": float(bk["entry"][i]),
                "stop": float(bk["stop"][i]),
                "tp": float(bk["tp"][i]),
                "xt": int(five["t"][j]),
                "xp": float(bk["exit_px"][i]),
                "r": round(float(bk["r"][i]), 4),
                "bps": round(float(bk["ret"][i]) * 1e4, 2),
                "hrs": round(float(bk["held"][i]) / 12, 2),
                "bar": i,                       # chi so nen tin hieu, dung khi sua lenh
                "bars": _slice_bars(bars, i),
            })
    trades.sort(key=lambda d: d["t"])
    for k, tr in enumerate(trades):
        tr["i"] = k

    r = np.array([t["r"] for t in trades]) if trades else np.zeros(0)
    bps = np.array([t["bps"] for t in trades]) if trades else np.zeros(0)
    summary = {
        "n_long": sum(1 for t in trades if t["side"] == "long"),
        "n_short": sum(1 for t in trades if t["side"] == "short"),
        "win_rate": float((r >= 1.99).mean()) if len(r) else 0.0,
        "gross_r": float(r.mean()) if len(r) else 0.0,
        "net_bps": float(bps.mean()) if len(bps) else 0.0,
    }
    if progress:
        progress("compute", 1, 1, f"{len(trades)} lenh")
    return {"config": cfg.as_dict(), "funnel": ev["funnel"],
            "trades": trades, "summary": summary}
```

- [ ] **Step 4: Chay test de chac chan no dat**

Run: `.venv/bin/python -m pytest tests/test_webapp_compute.py -q`
Expected: PASS, 7 passed (hoac 7 skipped neu chua co npz)

- [ ] **Step 5: Commit**

```bash
git add scripts/webapp/compute.py tests/test_webapp_compute.py
git commit -m "feat(webapp): compute trades for a config, each carrying its 6 bars

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `replay_one()` — tinh lai mot lenh sau khi sua TP/SL

**Files:**
- Modify: `scripts/webapp/compute.py` (them ham `replay_one`)
- Modify: `tests/test_webapp_compute.py` (them test khu hoi)

**Interfaces:**
- Consumes: `five` va `bars` tu `load()`
- Produces: `replay_one(five: dict, bars: dict, bar: int, side: str, tp: float, sl: float) -> dict` tra `{"r", "bps", "xt", "xp", "hrs"}`

- [ ] **Step 1: Viet test that bai (test khu hoi)**

Them vao cuoi `tests/test_webapp_compute.py`:
```python
@needs_data
def test_replay_with_original_levels_reproduces_the_original_result():
    """Rang buoc chong troi: neu replay_one va brackets tinh khac nhau, moi con
    so hien sau khi nguoi dung keo tay cam se khong con so sanh duoc voi con so
    truoc do."""
    from webapp.compute import replay_one

    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=3, wick=0.10, days=2100)
    five, bars = load(cfg, CACHE)
    out = run(cfg, CACHE)
    assert len(out["trades"]) >= 20

    for tr in out["trades"][:20]:
        got = replay_one(five, bars, tr["bar"], tr["side"], tr["tp"], tr["stop"])
        assert got["r"] == pytest.approx(tr["r"], abs=1e-4), f"lenh #{tr['i']}"
        assert got["bps"] == pytest.approx(tr["bps"], abs=1e-2)
        assert got["xt"] == tr["xt"]


@needs_data
def test_replay_with_a_nearer_target_never_loses_more():
    """Keo TP ve gan hon thi khong the bien mot lenh thang thanh lenh thua."""
    from webapp.compute import replay_one

    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=3, wick=0.10, days=2100)
    five, bars = load(cfg, CACHE)
    out = run(cfg, CACHE)
    winners = [t for t in out["trades"] if t["r"] >= 1.99][:10]
    assert winners, "phai co lenh thang de kiem"
    for tr in winners:
        sign = 1 if tr["side"] == "long" else -1
        r_price = (tr["entry"] - tr["stop"]) * sign
        nearer = tr["entry"] + sign * 1.0 * r_price      # TP 1R thay vi 2R
        got = replay_one(five, bars, tr["bar"], tr["side"], nearer, tr["stop"])
        assert got["r"] == pytest.approx(1.0, abs=1e-6)
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `.venv/bin/python -m pytest tests/test_webapp_compute.py -q -k replay`
Expected: FAIL voi `ImportError: cannot import name 'replay_one'`

- [ ] **Step 3: Them `replay_one` vao `compute.py`**

Them vao cuoi `scripts/webapp/compute.py`:
```python
def replay_one(five: dict, bars: dict, bar: int, side: str, tp: float,
               sl: float) -> dict:
    """Tinh lai MOT lenh voi TP/SL moi, tren dung duong gia 5m va dung quy uoc
    ma `backtest_taker_oi.brackets` dung: vao o gia mo nen ke tiep, quet nen 5m
    tu do, cham ca hai trong cung mot nen 5m thi tinh la THUA.

    Test `test_replay_with_original_levels_reproduces_the_original_result` ghim
    ham nay vao `brackets`; hai ben troi khoi nhau la test do do ngay.
    """
    sgn = 1 if side == "long" else -1
    entry = float(bars["o"][bar + 1])
    r = (entry - sl) * sgn
    if not np.isfinite(r) or r <= 0:
        return {"r": None, "bps": None, "xt": None, "xp": None, "hrs": None}

    a = int(bars["i0"][bar + 1])
    z = min(a + T.CAP_H * 12, len(five["l"]))
    lo5, hi5 = five["l"][a:z], five["h"][a:z]
    if sgn > 0:
        hit_s, hit_t = lo5 <= sl, hi5 >= tp
    else:
        hit_s, hit_t = hi5 >= sl, lo5 <= tp
    is_ = int(np.argmax(hit_s)) if hit_s.any() else 10 ** 9
    it_ = int(np.argmax(hit_t)) if hit_t.any() else 10 ** 9

    if is_ == it_ == 10 ** 9:
        k = z - 1
        out_r = (float(five["c"][k]) - entry) * sgn / r
        held, xp = z - a, float(five["c"][k])
    elif is_ <= it_:
        out_r, held, xp = -1.0, is_ + 1, sl
        k = a + is_
    else:
        out_r, held, xp = (tp - entry) * sgn / r, it_ + 1, tp
        k = a + it_
    return {"r": round(out_r, 4),
            "bps": round((out_r * (r / entry) - 2 * T.FEE) * 1e4, 2),
            "xt": int(five["t"][k]), "xp": xp, "hrs": round(held / 12, 2)}
```

- [ ] **Step 4: Chay test de chac chan no dat**

Run: `.venv/bin/python -m pytest tests/test_webapp_compute.py -q`
Expected: PASS, 9 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/webapp/compute.py tests/test_webapp_compute.py
git commit -m "feat(webapp): replay one trade with edited TP/SL on the 5m path

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `jobs.py` — chay nen, tien do, huy

**Files:**
- Create: `scripts/webapp/jobs.py`
- Create: `tests/test_webapp_jobs.py`

**Interfaces:**
- Consumes: khong (nhan `work` la mot callable, de test khong phai tai du lieu)
- Produces:
  - `Job` voi thuoc tinh `id: str`, `key: str`, `state: str` ("running" | "done" | "error" | "cancelled"), `phase: str`, `done: int`, `total: int`, `msg: str`, `error: str | None`
  - `JobRunner()` voi `start(key: str, work: Callable[[Progress, Callable[[], bool]], None]) -> Job`, `get(job_id) -> Job | None`, `by_key(key) -> Job | None`, `cancel(job_id) -> bool`
  - `Job.wait(timeout: float) -> None` — chi dung trong test

- [ ] **Step 1: Viet test that bai**

Tao `tests/test_webapp_jobs.py`:
```python
import time

from webapp.jobs import JobRunner


def test_job_runs_and_reports_progress():
    r = JobRunner()
    def work(progress, cancelled):
        for k in range(1, 4):
            progress("fetch", k, 3, f"buoc {k}")
    job = r.start("k1", work)
    job.wait(5)
    assert job.state == "done"
    assert (job.done, job.total) == (3, 3)


def test_error_is_captured_not_raised():
    r = JobRunner()
    def work(progress, cancelled):
        raise ValueError("hong that")
    job = r.start("k2", work)
    job.wait(5)
    assert job.state == "error"
    assert "hong that" in job.error


def test_cancel_stops_the_loop():
    r = JobRunner()
    def work(progress, cancelled):
        for k in range(1000):
            if cancelled():
                return
            progress("fetch", k, 1000, "")
            time.sleep(0.001)
    job = r.start("k3", work)
    time.sleep(0.05)
    assert r.cancel(job.id) is True
    job.wait(5)
    assert job.state == "cancelled"
    assert job.done < 1000


def test_second_start_on_same_key_returns_the_running_job():
    """Hai tab cung chon mot config phai bam vao cung mot job, khong tai hai lan."""
    r = JobRunner()
    def work(progress, cancelled):
        time.sleep(0.2)
    a = r.start("same", work)
    b = r.start("same", work)
    assert a.id == b.id
    a.wait(5)


def test_finished_job_is_not_reused_for_a_new_start():
    r = JobRunner()
    def work(progress, cancelled):
        pass
    a = r.start("k4", work)
    a.wait(5)
    b = r.start("k4", work)
    assert a.id != b.id
    b.wait(5)
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `.venv/bin/python -m pytest tests/test_webapp_jobs.py -q`
Expected: FAIL voi `ModuleNotFoundError: No module named 'webapp.jobs'`

- [ ] **Step 3: Viet `jobs.py`**

```python
"""Chay mot cong viec dai o luong nen, co tien do doc duoc va huy duoc.

Job duoc dinh danh theo KHOA CONFIG chu khong chi theo id: hai tab cung chon
mot config phai bam vao cung mot job, neu khong se tai du lieu hai lan song song
va ghi de len nhau.
"""
from __future__ import annotations

import threading
import traceback
import uuid
from typing import Callable

Progress = Callable[[str, int, int, str], None]
Work = Callable[[Progress, Callable[[], bool]], None]


class Job:
    def __init__(self, key: str):
        self.id = uuid.uuid4().hex[:12]
        self.key = key
        self.state = "running"
        self.phase = ""
        self.done = 0
        self.total = 0
        self.msg = ""
        self.error: str | None = None
        self._cancel = threading.Event()
        self._finished = threading.Event()

    def snapshot(self) -> dict:
        return {"job": self.id, "key": self.key, "state": self.state,
                "phase": self.phase, "done": self.done, "total": self.total,
                "msg": self.msg, "error": self.error}

    def wait(self, timeout: float) -> None:
        self._finished.wait(timeout)


class JobRunner:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._by_key: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start(self, key: str, work: Work) -> Job:
        with self._lock:
            cur = self._by_key.get(key)
            if cur is not None and cur.state == "running":
                return cur
            job = Job(key)
            self._jobs[job.id] = job
            self._by_key[key] = job

        def progress(phase: str, done: int, total: int, msg: str = "") -> None:
            job.phase, job.done, job.total, job.msg = phase, done, total, msg

        def target() -> None:
            try:
                work(progress, job._cancel.is_set)
                job.state = "cancelled" if job._cancel.is_set() else "done"
            except Exception:
                job.state = "error"
                job.error = traceback.format_exc(limit=3)
            finally:
                job._finished.set()

        threading.Thread(target=target, daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def by_key(self, key: str) -> Job | None:
        return self._by_key.get(key)

    def cancel(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.state != "running":
            return False
        job._cancel.set()
        return True
```

- [ ] **Step 4: Chay test de chac chan no dat**

Run: `.venv/bin/python -m pytest tests/test_webapp_jobs.py -q`
Expected: PASS, 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/webapp/jobs.py tests/test_webapp_jobs.py
git commit -m "feat(webapp): background job runner with progress and cancel

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `serve.py` — HTTP, SSE, dinh tuyen

**Files:**
- Create: `scripts/webapp/serve.py`
- Create: `tests/test_webapp_api.py`

**Interfaces:**
- Consumes: `webapp.rules.RuleConfig`, `webapp.store.Store/cache_key`, `webapp.compute.run/load/replay_one`, `webapp.jobs.JobRunner`
- Produces:
  - `make_server(cache_root: Path, port: int = 0) -> ThreadingHTTPServer` — `port=0` cho cong tam, dung trong test
  - `main()` doc `--port` (mac dinh 8900), `--cache` (mac dinh `reports/.cache/metrics`), bind `127.0.0.1`
  - Cac route trong spec

- [ ] **Step 1: Viet test that bai**

Tao `tests/test_webapp_api.py`:
```python
import json
import threading
import urllib.request
from pathlib import Path

import pytest

from webapp.serve import make_server


@pytest.fixture
def server(tmp_path):
    srv = make_server(tmp_path, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def get(base, path):
    with urllib.request.urlopen(base + path) as r:
        return r.status, json.loads(r.read())


def post(base, path, payload):
    req = urllib.request.Request(
        base + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())


def test_index_is_served(server):
    with urllib.request.urlopen(server + "/") as r:
        body = r.read().decode()
    assert r.status == 200
    assert "<title>" in body


def test_unknown_route_is_404(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(server + "/api/nope")
    assert e.value.code == 404


def test_run_rejects_unknown_timeframe(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        post(server, "/api/run", {"symbol": "BTCUSDT", "tf": "3m", "n": 5,
                                  "wick": 0.1, "days": 365})
    assert e.value.code == 400


def test_run_rejects_bad_n(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        post(server, "/api/run", {"symbol": "BTCUSDT", "tf": "1h", "n": 0,
                                  "wick": 0.1, "days": 365})
    assert e.value.code == 400


def test_result_for_unknown_key_is_404(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(server + "/api/result/deadbeef")
    assert e.value.code == 404


def test_cached_run_is_returned_without_a_job(server, tmp_path):
    """Dung Store truc tiep de gia lap mot lan chay truoc do."""
    from webapp.rules import RuleConfig
    from webapp.store import Store, cache_key

    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=5, wick=0.10, days=365)
    key = cache_key(cfg)
    Store(tmp_path).write_run(key, {"config": cfg.as_dict(), "funnel": {},
                                    "trades": [], "summary": {"n_long": 0}})
    status, body = post(server, "/api/run", cfg.as_dict())
    assert status == 200
    assert body["cached"] is True
    assert body["key"] == key

    status, res = get(server, f"/api/result/{key}")
    assert res["summary"]["n_long"] == 0
    assert res["edits"] == {}


def test_symbols_lists_what_is_on_disk(server, tmp_path):
    (tmp_path / "BTCUSDT").mkdir()
    (tmp_path / "BTCUSDT" / "BTCUSDT-365d-5m.npz").write_bytes(b"")
    (tmp_path / "ETHUSDT").mkdir()
    status, body = get(server, "/api/symbols")
    assert status == 200
    by = {r["symbol"]: r for r in body}
    assert by["BTCUSDT"]["days"] == [365] and by["BTCUSDT"]["ready"] is True
    assert by["ETHUSDT"]["ready"] is False


def test_edits_are_stored_and_cleared(server, tmp_path):
    from webapp.rules import RuleConfig
    from webapp.store import Store, cache_key

    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=5, wick=0.10, days=365)
    key = cache_key(cfg)
    Store(tmp_path).write_run(key, {"config": cfg.as_dict(), "funnel": {},
                                    "trades": [], "summary": {}})
    req = urllib.request.Request(
        f"{server}/api/edits/{key}", method="DELETE")
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `.venv/bin/python -m pytest tests/test_webapp_api.py -q`
Expected: FAIL voi `ModuleNotFoundError: No module named 'webapp.serve'`

- [ ] **Step 3: Viet `serve.py`**

```python
"""HTTP cuc bo: phuc vu trang tinh va API tinh lenh.

Chi bind 127.0.0.1. Mo ra mang la quyet dinh cua nguoi dung -- mot thu muc
cache va mot API tinh toan khong nen tu dong nhin thay duoc tu ca LAN.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import build_trading_data_ui as B

from .compute import load, replay_one, run
from .jobs import JobRunner
from .rules import RuleConfig
from .store import Store, cache_key

STATIC = Path(__file__).resolve().parent / "static"
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8"}
DAYS_ALLOWED = (365, 1095, 2100)


class Ctx:
    """Trang thai dung chung giua cac request. Cache `five`/`bars` theo
    (symbol, tf, days) de sua TP/SL khong phai doc lai npz 21 MB moi lan."""

    def __init__(self, cache_root: Path):
        self.cache_root = Path(cache_root)
        # Store dat NGAY duoi cache_root. Neu tro sang thu muc khac thi
        # test dung Store(tmp_path) va server se doc hai noi khac nhau.
        self.store = Store(self.cache_root)
        self.jobs = JobRunner()
        self.loaded: dict[tuple, tuple] = {}

    def bars_for(self, cfg: RuleConfig):
        k = (cfg.symbol, cfg.tf, cfg.days)
        if k not in self.loaded:
            self.loaded[k] = load(cfg, self.cache_root)
        return self.loaded[k]


def parse_config(raw: dict) -> RuleConfig:
    """Doi JSON thanh RuleConfig, nem ValueError kem thong bao doc duoc."""
    tf = str(raw.get("tf", "1h"))
    if tf not in B.PERIOD_MS:
        raise ValueError(f"timeframe khong ho tro: {tf}")
    n = int(raw.get("n", 5))
    if not 2 <= n <= 200:
        raise ValueError(f"n phai trong khoang 2..200, nhan duoc {n}")
    wick = float(raw.get("wick", 0.10))
    if not 0.0 <= wick <= 1.0:
        raise ValueError(f"wick phai trong khoang 0..1, nhan duoc {wick}")
    days = int(raw.get("days", 365))
    if days not in DAYS_ALLOWED:
        raise ValueError(f"days phai la mot trong {DAYS_ALLOWED}, nhan duoc {days}")
    sym = str(raw.get("symbol", "BTCUSDT")).upper()
    if not re.fullmatch(r"[A-Z0-9]{4,20}", sym):
        raise ValueError(f"symbol khong hop le: {sym}")
    return RuleConfig(symbol=sym, tf=tf, n=n, wick=wick, days=days,
                      buy_th=float(raw.get("buy_th", 0.60)),
                      sell_th=float(raw.get("sell_th", 0.40)))


def symbols_on_disk(cache_root: Path) -> list[dict]:
    """Symbol da co du lieu tren dia, kem cac do sau da tai xong."""
    out = []
    for d in sorted(Path(cache_root).glob("*")):
        if not d.is_dir():
            continue
        days = sorted(int(m.stem.split("-")[1][:-1])
                      for m in d.glob(f"{d.name}-*d-5m.npz"))
        out.append({"symbol": d.name, "days": days, "ready": bool(days)})
    return out


def make_handler(ctx: Ctx):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):        # bot tieng on tren stderr
            pass

        # ---- tien ich ----
        def _json(self, code: int, payload) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def _static(self, name: str) -> None:
            path = (STATIC / name).resolve()
            if not str(path).startswith(str(STATIC)) or not path.exists():
                self._json(404, {"error": "khong tim thay"})
                return
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(path.suffix, "text/plain"))
            self.send_header("Content-Length", str(len(body)))
            # Khong cache: sau moi lan sua file, trinh duyet phai lay ban moi.
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        # ---- dinh tuyen ----
        def do_GET(self) -> None:
            p = self.path.split("?")[0]
            if p == "/":
                return self._static("index.html")
            if p.startswith("/static/"):
                return self._static(p[len("/static/"):])
            if p == "/api/symbols":
                return self._json(200, symbols_on_disk(ctx.cache_root))
            m = re.fullmatch(r"/api/result/([0-9a-f]{16})", p)
            if m:
                key = m.group(1)
                data = ctx.store.read_run(key)
                if data is None:
                    return self._json(404, {"error": "chua co ket qua cho khoa nay"})
                return self._json(200, {**data, "edits": ctx.store.read_edits(key)})
            m = re.fullmatch(r"/api/stream/([0-9a-f]{12})", p)
            if m:
                return self._stream(m.group(1))
            return self._json(404, {"error": "khong co route nay"})

        def do_POST(self) -> None:
            p = self.path.split("?")[0]
            if p == "/api/run":
                return self._run()
            m = re.fullmatch(r"/api/cancel/([0-9a-f]{12})", p)
            if m:
                return self._json(200, {"ok": ctx.jobs.cancel(m.group(1))})
            return self._json(404, {"error": "khong co route nay"})

        def do_PUT(self) -> None:
            m = re.fullmatch(r"/api/trade/([0-9a-f]{16})/(\d+)", self.path.split("?")[0])
            if not m:
                return self._json(404, {"error": "khong co route nay"})
            return self._edit(m.group(1), int(m.group(2)))

        def do_DELETE(self) -> None:
            m = re.fullmatch(r"/api/edits/([0-9a-f]{16})", self.path.split("?")[0])
            if not m:
                return self._json(404, {"error": "khong co route nay"})
            ctx.store.clear_edits(m.group(1))
            return self._json(200, {"ok": True})

        # ---- xu ly ----
        def _run(self) -> None:
            try:
                cfg = parse_config(self._body())
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                return self._json(400, {"error": str(e)})
            key = cache_key(cfg)
            if ctx.store.read_run(key) is not None:
                return self._json(200, {"key": key, "cached": True, "job": None})

            def work(progress, cancelled):
                out = run(cfg, ctx.cache_root, progress)
                if not cancelled():
                    ctx.store.write_run(key, out)

            job = ctx.jobs.start(key, work)
            return self._json(200, {"key": key, "cached": False, "job": job.id})

        def _stream(self, job_id: str) -> None:
            job = ctx.jobs.get(job_id)
            if job is None:
                return self._json(404, {"error": "khong co job nay"})
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            last = None
            while True:
                snap = job.snapshot()
                if snap != last:
                    self.wfile.write(f"data: {json.dumps(snap)}\n\n".encode())
                    self.wfile.flush()
                    last = snap
                if job.state != "running":
                    return
                time.sleep(0.2)

        def _edit(self, key: str, idx: int) -> None:
            data = ctx.store.read_run(key)
            if data is None:
                return self._json(404, {"error": "chua co ket qua cho khoa nay"})
            try:
                body = self._body()
                tp, sl = float(body["tp"]), float(body["sl"])
            except (KeyError, ValueError, json.JSONDecodeError) as e:
                return self._json(400, {"error": f"can tp va sl: {e}"})
            hits = [t for t in data["trades"] if t["i"] == idx]
            if not hits:
                return self._json(404, {"error": f"khong co lenh #{idx}"})
            tr = hits[0]
            cfg = RuleConfig(**data["config"])
            five, bars = ctx.bars_for(cfg)
            out = replay_one(five, bars, tr["bar"], tr["side"], tp, sl)
            ctx.store.write_edit(key, idx, {"tp": tp, "sl": sl, **out})
            return self._json(200, out)

    return Handler


def make_server(cache_root: Path, port: int = 0) -> ThreadingHTTPServer:
    ctx = Ctx(Path(cache_root))
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(ctx))
    srv.daemon_threads = True
    return srv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8900)
    ap.add_argument("--cache", default="reports/.cache/metrics")
    a = ap.parse_args()
    srv = make_server(Path(a.cache), a.port)
    print(f"Trade Explorer: http://127.0.0.1:{srv.server_address[1]}/")
    srv.serve_forever()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Tao mot `index.html` toi thieu de test tinh chay duoc**

Tao `scripts/webapp/static/index.html`:
```html
<!doctype html>
<meta charset="utf-8">
<title>Trade Explorer</title>
<link rel="stylesheet" href="/static/app.css">
<main id="root"></main>
<script type="module" src="/static/app.js"></script>
```
Tao `scripts/webapp/static/app.css` rong va `scripts/webapp/static/app.js` rong (Task 8 se viet noi dung).

- [ ] **Step 5: Chay test de chac chan no dat**

Run: `.venv/bin/python -m pytest tests/test_webapp_api.py -q`
Expected: PASS, 8 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/webapp/serve.py scripts/webapp/static tests/test_webapp_api.py
git commit -m "feat(webapp): HTTP routes, SSE progress stream, config validation

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: `card.js` — ve mot the lenh va bat tay cam

**Files:**
- Create: `scripts/webapp/static/card.js`
- Create: `tests/test_card.mjs`

**Interfaces:**
- Produces (ES module):
  - `scales(bars, tp, sl, w, h)` -> `{x(t), y(p), lo, hi, bw}`
  - `pickLine(geom, px, py)` -> `"tp" | "sl" | null` — chon duong GAN NHAT trong `BAND = 10` don vi
  - `drawCard(svg, trade, opts)` -> `void`, ve 6 nen + duong TP/SL + tay cam
  - Hang so xuat khau: `BAND = 10`

- [ ] **Step 1: Viet test that bai**

Tao `tests/test_card.mjs`:
```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { scales, pickLine, BAND } from '../scripts/webapp/static/card.js';

const bars = Array.from({ length: 6 }, (_, k) => ({
  t: k * 3600000, o: 100, h: 102, l: 98, c: 101, v: 1,
}));

test('thang gia phu het TP, SL va toan bo nen', () => {
  const g = scales(bars, 110, 95, 200, 120);
  assert.ok(g.lo <= 95, 'phai chua SL');
  assert.ok(g.hi >= 110, 'phai chua TP');
});

test('gia cao ve cao hon tren man hinh', () => {
  const g = scales(bars, 110, 95, 200, 120);
  assert.ok(g.y(110) < g.y(95), 'y cua gia cao phai nho hon');
});

test('sau nen trai deu trong be ngang', () => {
  const g = scales(bars, 110, 95, 200, 120);
  assert.ok(g.x(bars[0].t) >= 0);
  assert.ok(g.x(bars[5].t) <= 200);
  const d1 = g.x(bars[1].t) - g.x(bars[0].t);
  const d2 = g.x(bars[5].t) - g.x(bars[4].t);
  assert.ok(Math.abs(d1 - d2) < 1e-6, 'khoang cach phai deu');
});

test('bat dung duong gan nhat khi TP va SL sat nhau', () => {
  const g = scales(bars, 101.0, 100.9, 200, 120);
  const yT = g.y(101.0), yS = g.y(100.9);
  assert.ok(Math.abs(yT - yS) < BAND, 'tinh huong can kiem: hai duong trong mot BAND');
  assert.equal(pickLine(g, 100, yT), 'tp');
  assert.equal(pickLine(g, 100, yS), 'sl');
});

test('bam xa ca hai duong thi khong bat gi', () => {
  const g = scales(bars, 110, 95, 200, 120);
  assert.equal(pickLine(g, 100, g.y(110) + BAND * 5), null);
});

test('bam ngoai be ngang thi khong bat gi', () => {
  const g = scales(bars, 110, 95, 200, 120);
  assert.equal(pickLine(g, -50, g.y(110)), null);
});
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `node --test tests/test_card.mjs`
Expected: FAIL voi `Cannot find module .../card.js`

- [ ] **Step 3: Viet `card.js`**

```js
/* Ve MOT the lenh: nen tin hieu + 5 nen ke, duong TP/SL, tay cam keo.
   Tach rieng khoi app.js vi day la cho duy nhat co logic hinh hoc va keo-tha,
   va vi no chay mot lan cho MOI the -- test duoc no bang nen gia lap, khong
   can server. */

export const BAND = 10;          // ban kinh bat duong, don vi viewBox
const PAD = { l: 4, r: 34, t: 8, b: 8 };
const UP = '#2EBD85', DOWN = '#F6465D', INK = '#EAECEF';

export function scales(bars, tp, sl, w, h) {
  let lo = Math.min(tp, sl), hi = Math.max(tp, sl);
  for (const b of bars) { lo = Math.min(lo, b.l); hi = Math.max(hi, b.h); }
  const pad = (hi - lo) * 0.08 || Math.abs(hi || 1) * 0.001 || 1;
  lo -= pad; hi += pad;
  const t0 = bars[0].t;
  const step = bars.length > 1 ? bars[1].t - bars[0].t : 1;
  const span = step * bars.length;
  const x = t => PAD.l + (w - PAD.l - PAD.r) * ((t - t0) + step / 2) / span;
  const y = p => PAD.t + (h - PAD.t - PAD.b) * (hi - p) / (hi - lo);
  const bw = Math.max(2, (w - PAD.l - PAD.r) / bars.length * 0.6);
  return { x, y, lo, hi, bw, w, h, tp, sl };
}

/* Chon duong GAN NHAT, khong phai duong kiem truoc. Thu tu `near(tp) ? ... :
   near(sl) ? ...` lam TP luon thang khi hai duong o gan nhau, va khi do mot
   trong hai duong khong the bat duoc. Loi nay da xay ra tren trang truoc. */
export function pickLine(geom, px, py) {
  if (px < 0 || px > geom.w) return null;
  const dT = Math.abs(py - geom.y(geom.tp));
  const dS = Math.abs(py - geom.y(geom.sl));
  if (Math.min(dT, dS) > BAND) return null;
  return dT <= dS ? 'tp' : 'sl';
}

const NS = 'http://www.w3.org/2000/svg';
const mk = (tag, attrs) => {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
};

export function drawCard(svg, trade, opts = {}) {
  const w = opts.w || 200, h = opts.h || 120;
  const tp = opts.tp != null ? opts.tp : trade.tp;
  const sl = opts.sl != null ? opts.sl : trade.stop;
  const g = scales(trade.bars, tp, sl, w, h);
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.textContent = '';

  // vung TP (xanh) va vung SL (do), neo o gia vao lenh
  const yE = g.y(trade.entry), yT = g.y(tp), yS = g.y(sl);
  const band = (ya, yb, fill) => svg.appendChild(mk('rect', {
    x: PAD.l, y: Math.min(ya, yb), width: w - PAD.l - PAD.r,
    height: Math.max(1, Math.abs(yb - ya)), fill,
  }));
  band(yE, yT, 'rgba(46,189,133,.13)');
  band(yE, yS, 'rgba(246,70,93,.13)');

  // nen dau tien la nen TIN HIEU -- to sang de phan biet voi 5 nen ke
  trade.bars.forEach((b, k) => {
    const col = b.c >= b.o ? UP : DOWN;
    const cx = g.x(b.t);
    svg.appendChild(mk('line', {
      x1: cx, x2: cx, y1: g.y(b.h), y2: g.y(b.l),
      stroke: col, 'stroke-width': 1, opacity: k === 0 ? 1 : 0.85,
    }));
    const yo = g.y(Math.max(b.o, b.c)), yc = g.y(Math.min(b.o, b.c));
    svg.appendChild(mk('rect', {
      x: cx - g.bw / 2, y: yo, width: g.bw,
      height: Math.max(1, yc - yo), fill: col, opacity: k === 0 ? 1 : 0.85,
    }));
  });

  // duong TP/SL keo het be ngang, kem nhan gia o mep phai
  const line = (y, col, dash) => svg.appendChild(mk('line', {
    x1: PAD.l, x2: w - PAD.r, y1: y, y2: y, stroke: col,
    'stroke-width': 1.4, 'stroke-dasharray': dash || '',
  }));
  line(yT, UP); line(yS, DOWN); line(yE, INK, '3 3');

  for (const [y, col] of [[yT, UP], [yS, DOWN]]) {
    svg.appendChild(mk('rect', {
      x: w - PAD.r + 2, y: y - 3, width: 8, height: 6, rx: 2, fill: col,
    }));
  }
  return g;
}
```

- [ ] **Step 4: Chay test de chac chan no dat**

Run: `node --test tests/test_card.mjs`
Expected: PASS, 6 pass 0 fail

- [ ] **Step 5: Commit**

```bash
git add scripts/webapp/static/card.js tests/test_card.mjs
git commit -m "feat(webapp): trade card geometry, drawing, nearest-line hit test

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: `app.js` — thanh config, luong chay, luoi the, lazy-load

**Files:**
- Modify: `scripts/webapp/static/index.html`
- Modify: `scripts/webapp/static/app.css`
- Modify: `scripts/webapp/static/app.js`

**Interfaces:**
- Consumes: `card.js` (`drawCard`), cac route `/api/run`, `/api/stream/<job>`, `/api/result/<key>`
- Produces: khong co API cho module khac; day la diem vao cua trang

- [ ] **Step 1: Viet `index.html`**

```html
<!doctype html>
<meta charset="utf-8">
<title>Trade Explorer</title>
<link rel="stylesheet" href="/static/app.css">
<header class="bar">
  <label>Symbol <input id="sym" value="BTCUSDT" size="10"></label>
  <label>TF <select id="tf">
    <option>5m</option><option>15m</option><option>30m</option>
    <option selected>1h</option><option>4h</option><option>1d</option></select></label>
  <label>n <input id="n" type="number" value="5" min="2" max="200" size="4"></label>
  <label>Râu ≤ <select id="wick">
    <option value="0">0%</option><option value="0.05">5%</option>
    <option value="0.1" selected>10%</option><option value="0.2">20%</option>
    <option value="1">bỏ qua</option></select></label>
  <label>Lịch sử <select id="days">
    <option value="365" selected>365 ngày</option>
    <option value="1095">1095 ngày</option>
    <option value="2100">2100 ngày</option></select></label>
  <button id="go">Chạy</button>
  <button id="stop" hidden>Hủy</button>
  <span id="status"></span>
</header>
<section id="funnel" hidden></section>
<section id="summary" hidden></section>
<section id="grid"></section>
<script type="module" src="/static/app.js"></script>
```

- [ ] **Step 2: Viet `app.css`**

```css
:root{--bg:#181A20;--line:#2B3139;--ink:#EAECEF;--mut:#848E9C;--up:#2EBD85;--dn:#F6465D}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.bar{display:flex;gap:14px;align-items:center;flex-wrap:wrap;
     padding:12px 16px;border-bottom:1px solid var(--line);position:sticky;top:0;
     background:var(--bg);z-index:2}
.bar label{color:var(--mut);display:flex;gap:6px;align-items:center}
.bar input,.bar select{background:#1E2329;color:var(--ink);border:1px solid var(--line);
     border-radius:4px;padding:5px 8px;font:inherit}
.bar button{background:#FCD535;color:#202630;border:0;border-radius:4px;
     padding:6px 14px;font:inherit;font-weight:600;cursor:pointer}
.bar button#stop{background:transparent;color:var(--mut);border:1px solid var(--line)}
#status{color:var(--mut)}
#funnel,#summary{padding:10px 16px;border-bottom:1px solid var(--line)}
#funnel table{border-collapse:collapse;font-variant-numeric:tabular-nums}
#funnel td{padding:1px 14px 1px 0}
#funnel td:nth-child(2),#funnel td:nth-child(3){text-align:right}
#funnel .drop{color:var(--dn)}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));
      gap:10px;padding:14px 16px}
.card{border:1px solid var(--line);border-radius:6px;padding:8px;min-height:170px}
.card h4{margin:0 0 4px;font-size:12px;font-weight:600;display:flex;
     justify-content:space-between;gap:8px}
.card .long{color:var(--up)}.card .short{color:var(--dn)}
.card svg{display:block;width:100%;height:auto;touch-action:none}
.card .foot{color:var(--mut);font-size:11px;margin-top:4px;display:flex;
     justify-content:space-between}
.card .win{color:var(--up)}.card .lose{color:var(--dn)}
.card.edited{border-color:#FCD535}
```

- [ ] **Step 3: Viet `app.js`**

```js
import { drawCard } from './card.js';

const $ = id => document.getElementById(id);
const state = { key: null, trades: [], edits: {}, job: null, es: null };

function config() {
  return {
    symbol: $('sym').value.trim().toUpperCase(),
    tf: $('tf').value,
    n: +$('n').value,
    wick: +$('wick').value,
    days: +$('days').value,
  };
}

async function api(path, opts) {
  const r = await fetch(path, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
  return body;
}

/* ---------- luong chay ---------- */
$('go').onclick = async () => {
  $('status').textContent = 'đang gửi…';
  $('grid').textContent = '';
  try {
    const { key, cached, job } = await api('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config()),
    });
    state.key = key;
    if (cached) return loadResult(key);
    state.job = job;
    $('stop').hidden = false;
    watch(job, key);
  } catch (e) {
    $('status').textContent = 'lỗi: ' + e.message;
  }
};

$('stop').onclick = async () => {
  if (state.job) await api(`/api/cancel/${state.job}`, { method: 'POST' });
};

function watch(job, key) {
  state.es?.close();
  const es = new EventSource(`/api/stream/${job}`);
  state.es = es;
  es.onmessage = ev => {
    const s = JSON.parse(ev.data);
    const pct = s.total ? Math.round(s.done / s.total * 100) : 0;
    $('status').textContent = `${s.phase} ${pct}% ${s.msg || ''}`;
    if (s.state === 'done') { es.close(); $('stop').hidden = true; loadResult(key); }
    if (s.state === 'error') { es.close(); $('stop').hidden = true;
      $('status').textContent = 'lỗi: ' + (s.error || '').split('\n').pop(); }
    if (s.state === 'cancelled') { es.close(); $('stop').hidden = true;
      $('status').textContent = 'đã hủy'; }
  };
  // EventSource tu ket noi lai khi server dong stream; dong han de khong tao
  // mot vong ket noi lai vo tan sau khi job ket thuc.
  es.onerror = () => { es.close(); $('stop').hidden = true; };
}

async function loadResult(key) {
  const res = await api(`/api/result/${key}`);
  state.trades = res.trades;
  state.edits = res.edits || {};
  $('status').textContent = `${res.trades.length} lệnh`;
  renderFunnel(res.funnel);
  renderSummary(res.summary);
  renderGrid(res.trades);
}

/* ---------- pheu dieu kien ---------- */
function renderFunnel(funnel) {
  if (!funnel || !funnel.long) { $('funnel').hidden = true; return; }
  const side = 'long';
  const rows = funnel[side].map(s => {
    const pct = s.pct == null ? '' : (s.pct * 100).toFixed(1) + '%';
    const cls = s.pct != null && s.pct < 0.2 ? ' class="drop"' : '';
    return `<tr><td>${s.name}</td><td>${s.left.toLocaleString()}</td>` +
           `<td${cls}>${pct}</td></tr>`;
  }).join('');
  $('funnel').innerHTML = `<table><caption style="text-align:left;color:#848E9C">` +
    `Phễu điều kiện — chiều MUA</caption>${rows}</table>`;
  $('funnel').hidden = false;
}

function renderSummary(s) {
  if (!s) { $('summary').hidden = true; return; }
  $('summary').innerHTML =
    `${s.n_long} mua · ${s.n_short} bán · thắng ${(s.win_rate * 100).toFixed(1)}%` +
    ` · R gộp ${s.gross_r.toFixed(3)} · bps ròng ${s.net_bps.toFixed(1)}`;
  $('summary').hidden = false;
}

/* ---------- luoi the + lazy-load ----------
   Ve khi the vao vung nhin, XOA khi no ra xa 2 man hinh. Nguong xoa rong hon
   nguong ve, neu khong thi cuon qua lai quanh mot bien se ve-xoa lien tuc. */
const io = new IntersectionObserver(entries => {
  for (const e of entries) {
    const el = e.target;
    if (e.isIntersecting) paint(el);
    else if (e.intersectionRatio === 0 && Math.abs(e.boundingClientRect.top)
             > 2 * window.innerHeight) clear(el);
  }
}, { rootMargin: '400px 0px' });

function paint(el) {
  if (el.dataset.painted === '1') return;
  const tr = state.trades[+el.dataset.i];
  const ed = state.edits[tr.i];
  drawCard(el.querySelector('svg'), tr,
           ed ? { tp: ed.tp, sl: ed.sl } : {});
  el.dataset.painted = '1';
}

function clear(el) {
  const svg = el.querySelector('svg');
  if (svg) svg.textContent = '';
  el.dataset.painted = '0';
}

function renderGrid(trades) {
  const grid = $('grid');
  grid.textContent = '';
  io.disconnect();
  const frag = document.createDocumentFragment();
  trades.forEach((tr, i) => {
    const el = document.createElement('div');
    el.className = 'card';
    el.dataset.i = i;
    const ed = state.edits[tr.i];
    if (ed) el.classList.add('edited');
    const res = ed || tr;
    const when = new Date(tr.t).toLocaleString('vi-VN',
      { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    el.innerHTML =
      `<h4><span class="${tr.side}">${tr.side === 'long' ? '▲ LONG' : '▼ SHORT'}` +
      ` #${tr.i + 1}</span><span>${when}</span></h4><svg></svg>` +
      `<div class="foot"><span class="${res.r >= 1.99 ? 'win' : 'lose'}">` +
      `${res.r >= 1.99 ? '+2R' : res.r <= -0.99 ? '−1R' : res.r + 'R'}</span>` +
      `<span>${res.bps > 0 ? '+' : ''}${res.bps} bps</span>` +
      `<span>${res.hrs}h</span></div>`;
    frag.appendChild(el);
  });
  grid.appendChild(frag);
  for (const el of grid.children) io.observe(el);
}
```

- [ ] **Step 4: Chay server va kiem bang mat**

```bash
.venv/bin/python -m scripts.webapp.serve --port 8900 &
```
Neu lenh tren bao `No module named scripts.webapp`, chay thay bang:
```bash
cd scripts && ../.venv/bin/python -m webapp.serve --port 8900 &
```
Mo `http://127.0.0.1:8900/`, dat `n=3`, `days=2100`, bam **Chạy**.
Expected: thanh trang thai chay qua `fetch` roi `compute`, sau do luoi hien ~100 the, moi the co 6 nen, hai duong TP/SL, va dong chan ghi `+2R` hoac `−1R`.

- [ ] **Step 5: Do lazy-load**

Trong Console cua trinh duyet:
```js
$$('#grid .card').length + ' the · ' +
  $$('#grid .card svg *').length + ' phan tu svg dang ton tai'
```
Expected: so phan tu svg phai NHO HON 3 lan so the nhan 20; neu bang so the nhan ~20 thi lazy-load khong hoat dong va phai sua lai truoc khi di tiep.

- [ ] **Step 6: Commit**

```bash
git add scripts/webapp/static/index.html scripts/webapp/static/app.css scripts/webapp/static/app.js
git commit -m "feat(webapp): config bar, run flow with SSE, funnel, lazy-loaded card grid

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Sua TP/SL tren the

**Files:**
- Modify: `scripts/webapp/static/card.js` (them `attachDrag`)
- Modify: `scripts/webapp/static/app.js` (goi `attachDrag`, gui PUT, hien hai dong tom tat)
- Modify: `tests/test_card.mjs` (them test chuyen doi toa do)

**Interfaces:**
- Consumes: `pickLine`, `scales` tu Task 7; route `PUT /api/trade/<key>/<i>` tu Task 6
- Produces: `attachDrag(svg, geom, handlers)` trong `card.js`, voi `handlers = {onDrag(kind, price), onDrop(kind, price)}`; `toPrice(geom, clientY, rect) -> number` xuat khau de test duoc

- [ ] **Step 1: Viet test that bai**

Them vao `tests/test_card.mjs`:
```js
import { toPrice } from '../scripts/webapp/static/card.js';

test('doi toa do con tro sang gia la nghich dao cua y()', () => {
  const g = scales(bars, 110, 95, 200, 120);
  const rect = { top: 0, height: 240 };          // hien thi gap doi viewBox
  for (const p of [96, 100, 105, 109]) {
    const clientY = g.y(p) * (rect.height / g.h) + rect.top;
    assert.ok(Math.abs(toPrice(g, clientY, rect) - p) < 1e-6,
      `gia ${p} phai quay lai chinh no`);
  }
});
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `node --test tests/test_card.mjs`
Expected: FAIL voi `The requested module ... does not provide an export named 'toPrice'`

- [ ] **Step 3: Them `toPrice` va `attachDrag` vao `card.js`**

Them vao cuoi `scripts/webapp/static/card.js`:
```js
/* Doi toa do con tro (pixel tren man hinh) sang gia. Phai chia lai theo ti le
   giua kich thuoc hien thi va viewBox: the duoc CSS keo gian nen hai he nay
   khong trung nhau. */
export function toPrice(geom, clientY, rect) {
  const vy = (clientY - rect.top) * (geom.h / rect.height);
  return geom.hi - (vy - PAD.t) / (geom.h - PAD.t - PAD.b) * (geom.hi - geom.lo);
}

export function attachDrag(svg, geom, handlers) {
  let kind = null;
  svg.onpointerdown = e => {
    const r = svg.getBoundingClientRect();
    const px = (e.clientX - r.left) * (geom.w / r.width);
    const py = (e.clientY - r.top) * (geom.h / r.height);
    kind = pickLine(geom, px, py);
    if (!kind) return;
    svg.setPointerCapture(e.pointerId);
    e.preventDefault();
  };
  svg.onpointermove = e => {
    const r = svg.getBoundingClientRect();
    if (!kind) {
      const px = (e.clientX - r.left) * (geom.w / r.width);
      const py = (e.clientY - r.top) * (geom.h / r.height);
      svg.style.cursor = pickLine(geom, px, py) ? 'ns-resize' : '';
      return;
    }
    handlers.onDrag(kind, toPrice(geom, e.clientY, r));
  };
  const stop = e => {
    if (!kind) return;
    handlers.onDrop(kind, toPrice(geom, e.clientY, svg.getBoundingClientRect()));
    kind = null;
    try { svg.releasePointerCapture(e.pointerId); } catch {}
  };
  svg.onpointerup = stop;
  svg.onpointercancel = stop;
}
```

- [ ] **Step 4: Chay test de chac chan no dat**

Run: `node --test tests/test_card.mjs`
Expected: PASS, 7 pass 0 fail

- [ ] **Step 5: Noi vao `app.js`**

Trong `scripts/webapp/static/app.js`, doi dong import dau tien:
```js
import { drawCard } from './card.js';
```
thanh:
```js
import { attachDrag, drawCard } from './card.js';
```

Thay ham `paint` bang:
```js
function paint(el) {
  if (el.dataset.painted === '1') return;
  const tr = state.trades[+el.dataset.i];
  const svg = el.querySelector('svg');
  const live = { tp: (state.edits[tr.i] || tr).tp,
                 sl: (state.edits[tr.i] || {}).sl ?? tr.stop };
  const geom = drawCard(svg, tr, live);
  attachDrag(svg, geom, {
    onDrag: (kind, price) => {
      live[kind] = price;
      drawCard(svg, tr, live);          // ve lai ngay, chua goi server
    },
    onDrop: async (kind, price) => {
      live[kind] = price;
      try {
        const res = await api(`/api/trade/${state.key}/${tr.i}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tp: live.tp, sl: live.sl }),
        });
        state.edits[tr.i] = { tp: live.tp, sl: live.sl, ...res };
        el.classList.add('edited');
        updateFoot(el, res);
        renderSummary(recomputeSummary());
      } catch (err) {
        $('status').textContent = 'lỗi khi tính lại: ' + err.message;
      }
    },
  });
  el.dataset.painted = '1';
}

function updateFoot(el, res) {
  el.querySelector('.foot').innerHTML =
    `<span class="${res.r >= 1.99 ? 'win' : 'lose'}">` +
    `${res.r >= 1.99 ? '+2R' : res.r <= -0.99 ? '−1R' : res.r + 'R'}</span>` +
    `<span>${res.bps > 0 ? '+' : ''}${res.bps} bps</span><span>${res.hrs}h</span>`;
}

/* Tom tat hien HAI dong: ban may tinh va ban da sua tay. Gop chung lai thi
   khong con biet con so nao la cua luat va con so nao la do minh keo. */
function recomputeSummary() {
  const orig = state.trades;
  const eff = orig.map(t => state.edits[t.i] || t);
  const stat = arr => ({
    n_long: orig.filter(t => t.side === 'long').length,
    n_short: orig.filter(t => t.side === 'short').length,
    win_rate: arr.filter(t => t.r >= 1.99).length / (arr.length || 1),
    gross_r: arr.reduce((s, t) => s + t.r, 0) / (arr.length || 1),
    net_bps: arr.reduce((s, t) => s + t.bps, 0) / (arr.length || 1),
  });
  return { ...stat(eff), edited: Object.keys(state.edits).length, base: stat(orig) };
}
```

Thay ham `renderSummary` bang:
```js
function renderSummary(s) {
  if (!s) { $('summary').hidden = true; return; }
  const fmt = x => `thắng ${(x.win_rate * 100).toFixed(1)}%` +
    ` · R gộp ${x.gross_r.toFixed(3)} · bps ròng ${x.net_bps.toFixed(1)}`;
  let html = `${s.n_long} mua · ${s.n_short} bán — ${fmt(s)}`;
  if (s.edited) {
    html = `<div>máy tính: ${s.n_long} mua · ${s.n_short} bán — ${fmt(s.base)}</div>` +
           `<div style="color:#FCD535">đã sửa ${s.edited} lệnh — ${fmt(s)}</div>`;
  }
  $('summary').innerHTML = html;
  $('summary').hidden = false;
}
```

- [ ] **Step 6: Kiem bang mat**

Chay lai server, chay mot config cho ra lenh, roi keo tay cam TP cua mot the.
Expected: duong TP chay theo con tro; tha ra thi dong chan doi so, vien the thanh vang, va dong tom tat tach thanh hai dong — mot dong "máy tính", mot dong "đã sửa N lệnh".
Tai lai trang va chay lai cung config: the do phai VAN con vien vang va van giu TP da sua.

- [ ] **Step 7: Chay toan bo test**

Run: `.venv/bin/python -m pytest tests/ -q && node --test tests/test_card.mjs`
Expected: moi test Python dat (tru cac test skip khi thieu npz), 7 test JS dat.

- [ ] **Step 8: Commit**

```bash
git add scripts/webapp/static/card.js scripts/webapp/static/app.js tests/test_card.mjs
git commit -m "feat(webapp): drag TP/SL on a card, recompute server-side, split summary

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: Huy duoc khi dang tai, va kiem symbol co that

Spec hua hai dieu ma chin task tren khong lam: nut Huy phai dung duoc **giua pha tai**, va symbol sai phai bi tra ve 400 thay vi tao mot job chay 11 phut roi hong. Ca hai deu can cham vao `backtest_taker_oi.dataset`, nen gom lai mot task.

**Files:**
- Modify: `scripts/backtest_taker_oi.py` (them tham so `progress` va `should_stop` cho `dataset`)
- Modify: `scripts/build_trading_data_ui.py` (them tham so `on_day` cho `archive_metrics`)
- Modify: `scripts/webapp/compute.py` (`load` va `run` nhan `should_stop`)
- Modify: `scripts/webapp/serve.py` (kiem symbol, truyen `cancelled` vao `run`)
- Create: `tests/test_webapp_cancel.py`

**Interfaces:**
- Consumes: `webapp.jobs` truyen `cancelled: Callable[[], bool]` vao `work`
- Produces:
  - `backtest_taker_oi.dataset(symbol, days, cache, progress=None, should_stop=None)` — nem `Cancelled` khi `should_stop()` tra `True`
  - `backtest_taker_oi.Cancelled(Exception)`
  - `build_trading_data_ui.archive_metrics(symbol, days, cache, workers=8, on_day=None)` — goi `on_day(done, total)` sau moi ngay tai xong
  - `webapp.serve.exchange_symbols(cache_root, fetch=None) -> set[str]`

- [ ] **Step 1: Viet test that bai**

Tao `tests/test_webapp_cancel.py`:
```python
import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from webapp.serve import exchange_symbols, make_server


def test_exchange_symbols_caches_to_disk(tmp_path):
    calls = []

    def fake_fetch():
        calls.append(1)
        return {"symbols": [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}]}

    a = exchange_symbols(tmp_path, fetch=fake_fetch)
    b = exchange_symbols(tmp_path, fetch=fake_fetch)
    assert a == {"BTCUSDT", "ETHUSDT"} == b
    assert len(calls) == 1, "lan thu hai phai doc tu dia"


def test_exchange_symbols_returns_empty_when_offline(tmp_path):
    """Mat mang thi KHONG duoc chan nguoi dung -- tra rong de bo qua kiem tra,
    con hon la khong chay duoc gi ca."""
    def boom():
        raise OSError("khong co mang")
    assert exchange_symbols(tmp_path, fetch=boom) == set()


@pytest.fixture
def server(tmp_path):
    srv = make_server(tmp_path, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_unknown_symbol_is_rejected_before_a_job_starts(server, tmp_path, monkeypatch):
    srv, base = server
    from webapp import serve as S
    monkeypatch.setattr(S, "exchange_symbols", lambda root, fetch=None: {"BTCUSDT"})
    req = urllib.request.Request(
        base + "/api/run",
        data=json.dumps({"symbol": "NOTACOIN", "tf": "1h", "n": 5,
                         "wick": 0.1, "days": 365}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req)
    assert e.value.code == 400
    assert "NOTACOIN" in e.value.read().decode()


def test_dataset_raises_cancelled_when_flag_flips():
    import sys
    sys.path.insert(0, "scripts")
    import backtest_taker_oi as T

    with pytest.raises(T.Cancelled):
        T.dataset("BTCUSDT", 365, Path("/tmp/khong-ton-tai-cache"),
                  should_stop=lambda: True)
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `.venv/bin/python -m pytest tests/test_webapp_cancel.py -q`
Expected: FAIL voi `ImportError: cannot import name 'exchange_symbols'`

- [ ] **Step 3: Them `Cancelled` va cac hook vao `backtest_taker_oi.dataset`**

Trong `scripts/backtest_taker_oi.py`, ngay truoc `def dataset(`, them:
```python
class Cancelled(Exception):
    """Nguoi dung bam Huy giua pha tai."""
```

Doi chu ky va than cua `dataset`. Doi:
```python
def dataset(symbol: str, days: int, cache: Path) -> dict:
    """5m OHLCV + open interest + ti le taker, gop ve mot luoi 5m."""
    f = cache / f"{symbol}-{days}d-5m.npz"
    if f.exists():
        return dict(np.load(f))

    want = int(days * 288)
    print(f"tai {want:,} nen 5m tu REST ...", flush=True)
    kl = B.klines_back(symbol, "5m", want)
```
thanh:
```python
def dataset(symbol: str, days: int, cache: Path, progress=None,
            should_stop=None) -> dict:
    """5m OHLCV + open interest + ti le taker, gop ve mot luoi 5m.

    `should_stop()` duoc hoi truoc moi pha va sau moi ngay kho tai xong; tra
    True thi nem `Cancelled`. Kiem theo tung ngay chu khong chi mot lan o dau
    la vi pha tai keo dai nhieu phut -- huy ma phai cho het thi khong phai huy.
    """
    f = cache / f"{symbol}-{days}d-5m.npz"
    if f.exists():
        return dict(np.load(f))

    stop = should_stop or (lambda: False)
    if stop():
        raise Cancelled()
    want = int(days * 288)
    if progress:
        progress("fetch", 0, days, f"tai {want:,} nen 5m")
    print(f"tai {want:,} nen 5m tu REST ...", flush=True)
    kl = B.klines_back(symbol, "5m", want)
    if stop():
        raise Cancelled()
```

Va doi dong goi `archive_metrics`. Doi:
```python
    arch = B.from_archive(B.archive_metrics(symbol, days, cache), vol, 0.0)
```
thanh:
```python
    def on_day(done: int, total: int) -> None:
        if stop():
            raise Cancelled()
        if progress:
            progress("fetch", done, total, f"kho metrics {done}/{total} ngay")

    arch = B.from_archive(
        B.archive_metrics(symbol, days, cache, on_day=on_day), vol, 0.0)
```

- [ ] **Step 4: Them `on_day` vao `archive_metrics`**

Trong `scripts/build_trading_data_ui.py`, doi:
```python
def archive_metrics(symbol: str, days: float, cache: Path, workers: int = 8) -> list[dict]:
    """Every archived 5m row over the requested span, oldest first."""
    cache.mkdir(parents=True, exist_ok=True)
    today = date.today()
    start = max(ARCHIVE_FROM, today - timedelta(days=int(days) + 1))
    span = [start + timedelta(days=i) for i in range((today - start).days + 1)]
    out: list[dict] = []
    with ThreadPoolExecutor(workers) as ex:
        for rows in ex.map(lambda d: archive_day(symbol, d, cache), span):
            if rows:
                out.extend(rows)
    return out
```
thanh:
```python
def archive_metrics(symbol: str, days: float, cache: Path, workers: int = 8,
                    on_day=None) -> list[dict]:
    """Every archived 5m row over the requested span, oldest first.

    `on_day(done, total)` is called after each day resolves. It may raise to
    abort the whole fetch -- that is how the webapp's Cancel button gets to
    interrupt a download that runs for minutes.
    """
    cache.mkdir(parents=True, exist_ok=True)
    today = date.today()
    start = max(ARCHIVE_FROM, today - timedelta(days=int(days) + 1))
    span = [start + timedelta(days=i) for i in range((today - start).days + 1)]
    out: list[dict] = []
    with ThreadPoolExecutor(workers) as ex:
        for k, rows in enumerate(ex.map(lambda d: archive_day(symbol, d, cache), span), 1):
            if rows:
                out.extend(rows)
            if on_day is not None:
                on_day(k, len(span))
    return out
```

- [ ] **Step 5: Truyen `should_stop` qua `compute.py`**

Trong `scripts/webapp/compute.py`, doi chu ky `load` va `run`:
```python
def load(cfg: RuleConfig, cache_root: Path, progress: Progress | None = None):
```
thanh:
```python
def load(cfg: RuleConfig, cache_root: Path, progress: Progress | None = None,
         should_stop=None):
```
va trong than `load`, doi:
```python
    five = T.dataset(cfg.symbol, cfg.days, Path(cache_root) / cfg.symbol)
```
thanh:
```python
    five = T.dataset(cfg.symbol, cfg.days, Path(cache_root) / cfg.symbol,
                     progress=progress, should_stop=should_stop)
```
Doi:
```python
def run(cfg: RuleConfig, cache_root: Path, progress: Progress | None = None) -> dict:
    five, bars = load(cfg, cache_root, progress)
```
thanh:
```python
def run(cfg: RuleConfig, cache_root: Path, progress: Progress | None = None,
        should_stop=None) -> dict:
    five, bars = load(cfg, cache_root, progress, should_stop)
```

- [ ] **Step 6: Kiem symbol va truyen `cancelled` trong `serve.py`**

Them vao `scripts/webapp/serve.py`, ngay truoc `def parse_config`:
```python
import urllib.request

SYMBOLS_TTL = 86_400          # danh sach symbol doi rat cham; mot ngay la du


def exchange_symbols(cache_root: Path, fetch=None) -> set[str]:
    """Tap symbol dang giao dich tren USDS-M, cache mot ngay.

    Mat mang thi tra RONG, va ben goi hieu rong la "khong kiem duoc" chu khong
    phai "khong co symbol nao" -- chan nguoi dung vi mot lan mat mang thi te
    hon la bo qua mot lan kiem.
    """
    path = Path(cache_root) / "exchange_symbols.json"
    if path.exists() and time.time() - path.stat().st_mtime < SYMBOLS_TTL:
        try:
            return set(json.loads(path.read_text()))
        except json.JSONDecodeError:
            pass

    def default_fetch():
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.loads(r.read())

    try:
        info = (fetch or default_fetch)()
        syms = sorted(s["symbol"] for s in info["symbols"])
    except Exception:
        return set()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(syms))
    return set(syms)
```

Trong `Handler._run`, doi:
```python
            key = cache_key(cfg)
            if ctx.store.read_run(key) is not None:
                return self._json(200, {"key": key, "cached": True, "job": None})

            def work(progress, cancelled):
                out = run(cfg, ctx.cache_root, progress)
                if not cancelled():
                    ctx.store.write_run(key, out)
```
thanh:
```python
            known = exchange_symbols(ctx.cache_root)
            if known and cfg.symbol not in known:
                return self._json(400, {
                    "error": f"{cfg.symbol} khong co tren Binance USDS-M"})
            key = cache_key(cfg)
            if ctx.store.read_run(key) is not None:
                return self._json(200, {"key": key, "cached": True, "job": None})

            def work(progress, cancelled):
                out = run(cfg, ctx.cache_root, progress, should_stop=cancelled)
                if not cancelled():
                    ctx.store.write_run(key, out)
```

Trong `jobs.py`, doi khoi `except` cua `target` de `Cancelled` khong bi bao la loi. Doi:
```python
            except Exception:
                job.state = "error"
                job.error = traceback.format_exc(limit=3)
```
thanh:
```python
            except Exception as e:
                # Cancelled la duong thoat binh thuong, khong phai loi -- bao
                # no la "error" thi giao dien se hien mot stack trace do loet
                # sau khi nguoi dung tu bam Huy.
                if type(e).__name__ == "Cancelled":
                    job.state = "cancelled"
                else:
                    job.state = "error"
                    job.error = traceback.format_exc(limit=3)
```

- [ ] **Step 7: Chay test de chac chan no dat**

Run: `.venv/bin/python -m pytest tests/test_webapp_cancel.py -q`
Expected: PASS, 4 passed

- [ ] **Step 8: Chay lai toan bo test de chac chan khong pha gi**

Run: `.venv/bin/python -m pytest tests/ -q && node --test tests/test_card.mjs`
Expected: moi test dat. Cac test cu cua `scripts/` (`tests/test_dataset.py` v.v.) van phai xanh — `dataset` co tham so moi nhung deu co mac dinh.

- [ ] **Step 9: Do lazy-load o quy mo spec yeu cau**

Chay server, chon `BTCUSDT / 1h / n=3 / wick=bo qua / 2100 ngay` de ra tren 1.000 lenh. Cuon het luoi, roi trong Console:
```js
const cards = document.querySelectorAll('#grid .card').length;
const nodes = document.querySelectorAll('#grid .card svg *').length;
console.log(cards, 'the ·', nodes, 'phan tu svg · ti le', (nodes / cards).toFixed(1));
```
Expected: `cards` tren 1.000, va `nodes / cards` phai duoi **20**. Mot the ve day du chiem ~25 phan tu, nen ti le duoi 20 nghia la phan lon the dang o trang thai da xoa. Neu ti le xap xi 25 thi lazy-load khong nha bo nho va phai sua truoc khi coi task nay la xong.

- [ ] **Step 10: Commit**

```bash
git add scripts/backtest_taker_oi.py scripts/build_trading_data_ui.py \
        scripts/webapp/compute.py scripts/webapp/serve.py scripts/webapp/jobs.py \
        tests/test_webapp_cancel.py
git commit -m "feat(webapp): cancellable fetch and symbol validation

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Gia so: doi tu luoi the sang chart (Task 11-13)

> Quyet dinh cua user sau review toan nhanh: *"toi thay dang sai roi, toi muon
> hien thi cac lenh long/short nay len chart truc tiep, khong phai qua the."*

**Muc tieu:** ve lenh TRUC TIEP len chart nen, thay cho luoi the nho.

**Cach lam:** tai dung phan ve chart cua `scripts/build_trading_data_ui.py` --
843 dong da chay on dinh qua nhieu vong sua -- thay vi viet chart thu ba.

**Giu nguyen:** toan bo backend (`rules.py`, `store.py`, `compute.py`,
`jobs.py`, `serve.py`), golden test, `replay_one`, `PUT /api/trade`, huy giua
chung, kiem symbol.

**Bo:** `card.js`, `lazyload.js`, luoi the, va ca tieu chi nghiem thu 1.000 the
-- no do mot dai luong ma thiet ke moi khong sinh ra.

## Su that ve doan code se tai dung

Do truoc khi lap ke hoach, de khong ai tuong day la mot module sach:

| | |
|---|---|
| Kich thuoc | 843 dong, 42 KB |
| Dinh danh top-level | 51 |
| Id DOM chot cung | 10 (`#cards`, `#tf`, `#span`, `#trade`, `#tnav`, `#tprev`, `#tnext`, `#now`, `#range`, `#pinned`) |
| Diem vao du lieu | 1 (`const D = __DATA__`) |
| `await` / `return` o top-level | khong co |
| Dong khoi dong cuoi | `clamp(); fillSpan(); renderAll();` |

Vi khong co `await`/`return` o top-level nen boc duoc bang mot ham. Nhung 10 id
kia VAN chot cung: trang Trade Explorer phai cung cap dung nhung id do. Day la
"dung lai", khong phai "component hoa" -- dung hua nhieu hon the.

---

### Task 11: Tach chart thanh `static/chart.js`, builder nhung lai

**Files:**
- Create: `scripts/webapp/static/chart.js`
- Modify: `scripts/build_trading_data_ui.py` (bo khoi JS, doc file va nhung vao)
- Create: `tests/test_chart_extract.py`

**Interfaces:**
- Produces: `chart.js` xuat `export function initChart(D)`. `D` la dung cau
  truc `collect()` sinh ra. Ham tu tim cac phan tu DOM theo id va tu goi
  `clamp(); fillSpan(); renderAll();` o cuoi.

- [ ] **Step 1: Viet test that bai**

`tests/test_chart_extract.py`:
```python
"""Tach chart ra file rieng khong duoc lam doi trang da dung.

`trading_data.html` la trang nguoi dung dang dung that. Test nay so DU LIEU
nhung trong trang truoc va sau khi tach, va kiem trang van tu chua (khong con
tham chieu file ngoai).
"""
import json
import re
from pathlib import Path

import pytest

CHART = Path("scripts/webapp/static/chart.js")


def test_chart_module_exists_and_exports_init():
    assert CHART.exists(), "chua tach chart.js"
    src = CHART.read_text(encoding="utf-8")
    assert "export function initChart(D)" in src


def test_chart_module_has_no_build_time_placeholder():
    """`__DATA__` la cho builder thay du lieu vao. Neu no con trong module thi
    module khong doc lap duoc voi builder."""
    assert "__DATA__" not in CHART.read_text(encoding="utf-8")


def test_builder_inlines_the_module_and_stays_self_contained():
    import sys
    sys.path.insert(0, "scripts")
    import build_trading_data_ui as B

    html = B.HTML
    assert "initChart(" in html, "builder phai goi initChart"
    assert "src=" not in html.split("<script")[-1][:200], \
        "trang phai tu chua, khong tham chieu file ngoai"
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `.venv/bin/python -m pytest tests/test_chart_extract.py -q`
Expected: FAIL — `chua tach chart.js`

- [ ] **Step 3: Tach**

Lay nguyen khoi giua `<script>` va `</script>` cuoi cung trong `HTML` cua
`build_trading_data_ui.py`, chuyen vao `scripts/webapp/static/chart.js`:
- doi dong `const D = __DATA__;` thanh tham so cua ham
- boc toan bo phan con lai trong `export function initChart(D) { ... }`
- **KHONG doi bat ky logic nao khac**

Trong builder, thay khoi `<script>...</script>` do bang doan doc file va nhung:
```python
CHART_JS = Path(__file__).resolve().parent / "webapp" / "static" / "chart.js"
```
va luc dung trang, nhung noi dung file (da bo dong `export `) kem mot loi goi
`initChart(<du lieu>)`. Trang phai van la mot file tu chua.

- [ ] **Step 4: Chay test**

Run: `.venv/bin/python -m pytest tests/test_chart_extract.py -q`
Expected: PASS, 3 passed

- [ ] **Step 5: Chung minh trang khong doi**

Dung lai trang va so DU LIEU nhung trong no voi ban truoc khi tach:
```bash
cp reports/trading_data.html /tmp/before.html
python3 scripts/build_trading_data_ui.py --days 365 --period 1h \
        --trades reports/trades_trend.json --compare ETHUSDT
python3 - <<'PY'
import json, pathlib
def data(p):
    s = pathlib.Path(p).read_text(encoding="utf-8")
    i = s.index("initChart(") + len("initChart(")
    return json.loads(s[i:s.rindex(")")])
PY
```
Neu ban truoc dung `const D = ...` con ban sau dung `initChart(...)` thi viet
ham doc cho ca hai dang. Bao cao ket qua so sanh -- du lieu phai giong het.

Kiem cu phap module bang Node (khong can trinh duyet):
`node --input-type=module -e "import('./scripts/webapp/static/chart.js').then(m=>console.log(typeof m.initChart))"`
Expected: `function`

- [ ] **Step 6: Commit**

```bash
git add scripts/webapp/static/chart.js scripts/build_trading_data_ui.py tests/test_chart_extract.py
git commit -m "refactor: extract the chart into a reusable module

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12: `GET /api/chart` va bo 6 nen trong moi lenh

**Files:**
- Modify: `scripts/webapp/serve.py` (them route)
- Modify: `scripts/webapp/compute.py` (bo `bars` khoi ban ghi lenh)
- Modify: `tests/test_webapp_compute.py`, `tests/test_webapp_api.py`

**Interfaces:**
- Produces: `GET /api/chart?symbol=&tf=&days=` -> dung cau truc `collect()` sinh
  ra (`candles, oi, taker, topAcc, topPos, global, basis, funding, stepMs,
  symbol, seam, lastFundingRate`). Validate tham so bang chinh `parse_config`.
- Ban ghi lenh khong con truong `bars`; truong `bar` (chi so nen tin hieu) GIU
  LAI vi `PUT /api/trade` dung no.

- [ ] **Step 1: Viet test that bai**

Them vao `tests/test_webapp_api.py`:
```python
def test_chart_returns_every_series_the_chart_needs(server, tmp_path):
    """Chart doc 8 chuoi. Thieu mot chuoi thi the tuong ung trang tron ma
    khong bao loi -- nen liet ke tuong minh o day."""
    import urllib.request, json
    url = f"{server}/api/chart?symbol=BTCUSDT&tf=1h&days=365"
    with urllib.request.urlopen(url) as r:
        body = json.loads(r.read())
    for key in ("candles", "oi", "taker", "topAcc", "topPos",
                "global", "basis", "funding", "stepMs", "symbol"):
        assert key in body, f"thieu chuoi {key}"
    assert body["candles"], "candles rong"


def test_chart_rejects_a_bad_timeframe(server):
    import urllib.error, urllib.request
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(f"{server}/api/chart?symbol=BTCUSDT&tf=3m&days=365")
    assert e.value.code == 400
```

Trong `tests/test_webapp_compute.py`, doi test dang khang dinh moi lenh mang 6
nen thanh khang dinh **khong con** truong `bars`, va truong `bar` van con:
```python
@needs_data
def test_trades_no_longer_carry_their_own_bars():
    """Chart ve tu chuoi nen day du, nen 6 nen nhet trong moi lenh la thua."""
    cfg = RuleConfig(symbol="BTCUSDT", tf="1h", n=3, wick=0.10, days=2100)
    out = run(cfg, CACHE)
    assert out["trades"]
    for tr in out["trades"]:
        assert "bars" not in tr
        assert isinstance(tr["bar"], int), "PUT /api/trade van can `bar`"
```

- [ ] **Step 2: Chay test de chac chan no that bai**

Run: `.venv/bin/python -m pytest tests/test_webapp_api.py tests/test_webapp_compute.py -q`
Expected: FAIL — chua co route `/api/chart`, va lenh van con `bars`

- [ ] **Step 3: Trien khai**

Trong `compute.py`, bo `"bars": _slice_bars(...)` khoi ban ghi lenh. Xoa
`_slice_bars` va `BARS_AFTER` neu khong con cho nao dung -- va xoa ca test cua
chung. Giu truong `bar`.

Trong `serve.py`, them route `GET /api/chart`. Doc tham so tu query string,
validate bang `parse_config` (tra 400 kem thong bao khi sai), roi goi ham
`collect()` cua `build_trading_data_ui` va tra JSON. Dung lai `Ctx` de khong
tai lai du lieu da nap.

- [ ] **Step 4: Chay test**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS. Cac test data-dependent phai CHAY, khong duoc skip.

- [ ] **Step 5: Commit**

```bash
git add scripts/webapp/serve.py scripts/webapp/compute.py tests/
git commit -m "feat(webapp): serve chart series from one endpoint, drop per-trade bars

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 13: Trang Trade Explorer dung chart

**Files:**
- Modify: `scripts/webapp/static/index.html`, `app.css`, `app.js`
- Modify: `scripts/webapp/static/chart.js` (cho phep nap lai lenh)
- Delete: `scripts/webapp/static/card.js`, `scripts/webapp/static/lazyload.js`,
  `tests/test_card.mjs`, `tests/test_lazyload.mjs`

- [ ] **Step 1: Trang phai co du 10 id chart doi**

`index.html` giu thanh config hien tai (symbol, tf, n, wick, days, nut Chay,
nut Huy, dong trang thai, pheu) va **them** cac phan tu chart doi:
`#cards`, `#pinned`, `#tf`, `#span`, `#now`, `#range`, `#tnav`, `#trade`,
`#tprev`, `#tnext`. Chart tu dung noi dung vao `#cards`.

Luu y xung dot: thanh config da co mot `#tf`. Chart cung doi `#tf`. Dung MOT
phan tu cho ca hai -- doi timeframe la doi ca config lan chart. Neu tach ra hai
phan tu, hai ben se lech nhau ma khong ai bao.

- [ ] **Step 2: `app.js` nap chart sau khi chay xong**

Sau khi `/api/result/<key>` tra ve, goi `/api/chart` voi cung symbol/tf/days,
gan `trades` tu ket qua vao `D`, roi goi `initChart(D)`.

- [ ] **Step 3: Keo TP/SL tren chart goi PUT**

Chart da co `pick()` chon duong gan nhat va co lop ve lenh (`kind:'trades'`).
Lam lop do keo duoc: khi tha, goi `PUT /api/trade/<key>/<i>` va cap nhat lenh
tai cho. Ap dung ca hai rang buoc da hoc o luoi the:
- kep SL khong duoc cham/vuot gia vao (server tra 400 cho truong hop suy bien)
- `PUT` hong thi khoi phuc ve muc server dang giu, va bao loi o dong trang thai

- [ ] **Step 4: Xoa phan khong con dung**

```bash
git rm scripts/webapp/static/card.js scripts/webapp/static/lazyload.js \
       tests/test_card.mjs tests/test_lazyload.mjs
```

- [ ] **Step 5: Kiem**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS.

Kiem bang trinh duyet la viec cua CONTROLLER, khong phai cua implementer --
Chrome tren may nay dang mo tab ca nhan cua user. Bao cao ro nhung gi chua kiem.

- [ ] **Step 6: Commit**

```bash
git add -u && git add scripts/webapp/static
git commit -m "feat(webapp): draw trades on the candle chart, drop the card grid

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
