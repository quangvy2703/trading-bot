"""Cau hinh HIEU LUC = bo da chot trong docs + phan nguoi dung ghi de.

Vi sao phai tach ra: hai bo tham so trong docs duoc chon kem ke toan da phep
thu (≈418 o RSI(2), 276 o dong luong — § Boi so phep thu trong docs). Sua mot con so la ket qua that
khong con duoc bao chung boi nghien cuu nua. Nen moi gia tri deu di kem gia
tri DA CHOT, va he luon noi ro dang chay lech bao nhieu o.
"""
from __future__ import annotations

from . import db
from .config import CFG, RSI2 as LOCK_RSI2, XSMOM as LOCK_XSMOM

KEY = "overrides"

# ten -> (nhom, kieu, min, max, mo ta)
SPEC = {
    # --- phan bo von ---
    # He so nhan cho 1R cua tung chien luoc. 0 = TAT han chien luoc do (vi
    # the dang mo cua no se duoc dong o luot chay ke tiep). Khong con la "ty
    # trong von": dinh co theo R khong chia von cho ai ca.
    # Tran 50 chu khong 5: RSI(2) dang chay o 8, va bang quet trong docs/
    # money-management-r.md § Ghep hai chien luoc di toi 32 (so k* = 32 cu
    # dem trung lenh, xem muc SUA o do).
    "alloc_rsi2":      ("alloc", float, 0.0, 50.0, "hệ số 1R cho RSI(2) — 0 là tắt"),
    "alloc_xsmom":     ("alloc", float, 0.0, 50.0, "hệ số 1R cho động lượng — 0 là tắt"),
    # --- RSI(2) ---
    "rsi2.topn":       ("rsi2", int, 1, 200, "vũ trụ top N thanh khoản"),
    "rsi2.slots":      ("rsi2", int, 1, 50, "số chỗ (N)"),
    "rsi2.rsi_in":     ("rsi2", float, 1.0, 50.0, "vào khi RSI(2) <"),
    "rsi2.rsi_out":    ("rsi2", float, 50.0, 99.0, "thoát khi RSI(2) >"),
    "rsi2.ma":         ("rsi2", int, 2, 400, "lọc xu hướng close > MA"),
    "rsi2.atr":        ("rsi2", int, 2, 100, "chu kỳ ATR"),
    "rsi2.atr_k":      ("rsi2", float, 0.5, 20.0, "bội ATR cho cắt lỗ"),
    "rsi2.cap":        ("rsi2", float, 0.05, 0.95, "trần cắt lỗ (tỷ lệ)"),
    "rsi2.min_bars":   ("rsi2", int, 30, 1000, "số nến lịch sử tối thiểu"),
    "rsi2.layers":     ("rsi2", int, 1, 5, "số lớp mỗi mã — 1 là không mua thêm"),
    "rsi2.stop_hvn":   ("rsi2", int, 0, 1, "cắt lỗ ở đỉnh khối lượng HVN — 0 là 6×ATR"),
    "rsi2.vp_days":    ("rsi2", int, 3, 60, "số ngày nến 1H dựng volume profile"),
    "rsi2.vp_bin":     ("rsi2", float, 0.1, 2.0, "độ rộng ô profile (× ATR)"),
    "rsi2.vp_buf":     ("rsi2", float, 0.0, 2.0, "đệm dưới HVN (× ATR)"),
    # --- dong luong cat ngang ---
    "xsmom.topn":      ("xsmom", int, 5, 500, "vũ trụ top N thanh khoản"),
    "xsmom.lookback":  ("xsmom", int, 5, 365, "chân trời chấm điểm (ngày)"),
    "xsmom.frac":      ("xsmom", float, 0.02, 0.50, "tỷ lệ mỗi chân"),
    "xsmom.legs":      ("xsmom", int, 1, 25, "số mã tối thiểu mỗi chân"),
    "xsmom.sleeves":   ("xsmom", int, 1, 14, "số sổ lệch ngày"),
    "xsmom.hold":      ("xsmom", int, 1, 60, "số ngày giữ / nhịp tái cân bằng"),
    "xsmom.min_bars":  ("xsmom", int, 30, 1000, "số nến lịch sử tối thiểu"),
    "xsmom.ma":        ("xsmom", int, 0, 400, "lọc xu hướng theo MA — 0 là tắt"),
    # --- tran rui ro ---
    "max_gross_usd":   ("risk", float, 0.0, 1e9, "trần tổng mở thêm mỗi lượt"),
    "max_order_usd":   ("risk", float, 0.0, 1e9, "trần giá trị một lệnh"),
    "max_orders_per_run": ("risk", int, 1, 500, "trần số lệnh mỗi lượt"),
    # --- don vi rui ro: 1R la so USD mat khi cham diem cat lo ---
    "risk_r_usd":      ("risk", float, 1.0, 1e6, "1R — số USD rủi ro mỗi lệnh"),
    "risk_max_open":   ("risk", int, 1, 500, "số lệnh mở tối đa cùng lúc"),
}


def locked() -> dict:
    """Bo DA CHOT theo docs — moc so sanh, khong bao gio doi tu UI."""
    d = {"alloc_rsi2": CFG.alloc_rsi2, "alloc_xsmom": CFG.alloc_xsmom,
         "max_gross_usd": CFG.max_gross_usd, "max_order_usd": CFG.max_order_usd,
         "max_orders_per_run": CFG.max_orders_per_run,
         "risk_r_usd": CFG.risk_r_usd, "risk_max_open": CFG.risk_max_open}
    for k, v in LOCK_RSI2.items():
        d[f"rsi2.{k}"] = v
    for k, v in LOCK_XSMOM.items():
        d[f"xsmom.{k}"] = v
    return d


def overrides() -> dict:
    return db.kv_get(KEY, {}) or {}


def effective() -> dict:
    d = locked()
    d.update({k: v for k, v in overrides().items() if k in SPEC})
    return d


def drift() -> list:
    """Cac o dang lech khoi bo da chot."""
    lk, ef = locked(), effective()
    return [{"key": k, "locked": lk[k], "now": ef[k], "desc": SPEC[k][4]}
            for k in SPEC if k in lk and ef[k] != lk[k]]


def strat() -> tuple[dict, dict]:
    e = effective()
    r = {k: e[f"rsi2.{k}"] for k in LOCK_RSI2}
    x = {k: e[f"xsmom.{k}"] for k in LOCK_XSMOM}
    return r, x


def risk() -> dict:
    e = effective()
    return {"gross": e["max_gross_usd"], "order": e["max_order_usd"],
            "orders": int(e["max_orders_per_run"]),
            "r_usd": e["risk_r_usd"], "max_open": int(e["risk_max_open"])}


def alloc() -> dict:
    e = effective()
    return {"rsi2": e["alloc_rsi2"], "xsmom": e["alloc_xsmom"]}


def validate(patch: dict) -> dict:
    """Kiem kieu va khoang. Nem ValueError kem thong diep tieng Viet."""
    out = {}
    for k, v in patch.items():
        if k not in SPEC:
            raise ValueError(f"không có tham số «{k}»")
        _, typ, lo, hi, desc = SPEC[k]
        try:
            v = typ(v)
        except (TypeError, ValueError):
            raise ValueError(f"«{desc}» phải là "
                             f"{'số nguyên' if typ is int else 'số'}")
        if not (lo <= v <= hi):
            raise ValueError(f"«{desc}» phải nằm trong [{lo}, {hi}], nhận {v}")
        out[k] = v
    merged = {**effective(), **out}
    if merged["alloc_rsi2"] <= 0 and merged["alloc_xsmom"] <= 0:
        raise ValueError("tắt cả hai chiến lược thì không còn gì để chạy — "
                         "để ít nhất một hệ số 1R lớn hơn 0")
    if merged["xsmom.sleeves"] != merged["xsmom.hold"]:
        raise ValueError("số sổ phải bằng số ngày giữ, nếu không các sổ sẽ "
                         "chồng lấn hoặc để hở ngày không có sổ nào tái cân bằng")
    return out


def save(patch: dict) -> dict:
    ok = validate(patch)
    cur = overrides()
    cur.update(ok)
    # bo nhung o da quay ve dung bang bo chot cho gon
    lk = locked()
    cur = {k: v for k, v in cur.items() if k in lk and v != lk[k]}
    db.kv_set(KEY, cur)
    for k, v in sorted(ok.items()):
        db.log("warn", f"đổi tham số {k}: {lk.get(k)} → {v}")
    return cur


def reset() -> None:
    db.kv_set(KEY, {})
    db.log("warn", "trả toàn bộ tham số về bộ đã chốt trong docs")
