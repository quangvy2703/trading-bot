"""Cau hinh doc tu bien moi truong. Khong co gia tri bi mat nao nam trong ma."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _f(k: str, d: float) -> float:
    try:
        return float(os.environ.get(k, d))
    except ValueError:
        return d


def _i(k: str, d: int) -> int:
    try:
        return int(os.environ.get(k, d))
    except ValueError:
        return d


@dataclass(frozen=True)
class Config:
    db_path: str = os.environ.get("DB_PATH", "/data/live.db")
    seed_dir: str = os.environ.get("SEED_DIR", "/seed")
    run_at_utc: str = os.environ.get("RUN_AT_UTC", "00:05")

    # --- cong tac chay that, LOP KHOA THU NHAT (tang ma) ---
    # Bat trong UI khong du. Bien nay phai bang 1 thi ham dat lenh moi ton tai
    # duong chay. Muon doi phai sua compose va dung lai container -- mot hanh
    # dong co y thuc, khong phai mot cu bam nham.
    live_enabled_env: bool = os.environ.get("LIVE_TRADING_ENABLED", "0") == "1"

    binance_env: str = os.environ.get("BINANCE_ENV", "testnet")
    api_key: str = os.environ.get("BINANCE_API_KEY", "")
    api_secret: str = os.environ.get("BINANCE_API_SECRET", "")

    # --- tran rui ro, ap TRUOC khi gui bat ky lenh nao ---
    max_gross_usd: float = _f("MAX_GROSS_USD", 500)
    max_order_usd: float = _f("MAX_ORDER_USD", 150)
    max_orders_per_run: int = _i("MAX_ORDERS_PER_RUN", 40)

    # --- don vi rui ro (docs/money-management-r.md) ---
    # 1R = so USD mat khi cham diem cat lo. Co lenh = r_usd / rfrac, nen no
    # KHONG phu thuoc von: von chi quyet dinh mo duoc bao nhieu lenh cung luc.
    risk_r_usd: float = _f("RISK_R_USD", 2)
    risk_max_open: int = _i("RISK_MAX_OPEN", 33)       # 28 dong luong + 5 RSI(2)

    # He so nhan cho 1R, khong phai ty trong von. 0 = tat chien luoc.
    # RSI(2) = 8 — xem docs/money-management-r.md § Ghep hai chien luoc.
    alloc_rsi2: float = _f("ALLOC_RSI2", 8.0)
    alloc_xsmom: float = _f("ALLOC_XSMOM", 1.0)
    start_equity: float = _f("START_EQUITY_USD", 500)

    # --- ky quy: app TU DAT, khong tin thiet lap san co tren tai khoan ---
    # Moi ma deu chay CHEO: lo cua mot vi the do ca vi ganh, nen khong vi the
    # nao bi thanh ly rieng le. Trong che do cheo, don bay chi quyet dinh bao
    # nhieu ky quy ban dau bi giu, khong doi rui ro (rui ro = co lenh = 1R/R).
    # 5x: tong phoi nhiem dinh ~1,8x von chi giu ~36% vi, con du cho lenh moi.
    # Ma ket o ISOLATED (co vi the nen san khong cho doi) duoc nap them cho toi
    # khi don bay thuc <= muc nay.
    leverage: int = _i("LEVERAGE", 5)

    @property
    def rest(self) -> str:
        return ("https://testnet.binancefuture.com"
                if self.binance_env == "testnet"
                else "https://fapi.binance.com")

    @property
    def public_rest(self) -> str:
        # Du lieu nen/funding luon lay tu endpoint THAT: testnet khong co du
        # lich su de tinh MA20/ATR14/dong luong 30 ngay.
        return "https://fapi.binance.com"

    def stream(self, mode: str) -> str:
        """Luong gia danh dau (mark) cho lai/lo song tren bang vi the.

        Vi the chay that tren testnet khop o gia testnet — doc gia that thi
        lai/lo lech dung bang chenh lech hai san. So giay vao o gia that nen
        doc luong that."""
        return ("wss://fstream.binancefuture.com"
                if mode == "live" and self.binance_env == "testnet"
                else "wss://fstream.binance.com")

    def has_keys(self) -> bool:
        return bool(self.api_key and self.api_secret)


CFG = Config()

# --- tham so chien luoc, chot theo docs/rsi2-connors.md va xsmom-volnorm.md ---
RSI2 = {
    "topn": 10, "slots": 5, "rsi_in": 10.0, "rsi_out": 70.0,
    "ma": 20, "atr": 14, "atr_k": 6.0, "cap": 0.40, "min_bars": 205,
    # So lop toi da moi ma: 1 = khong mua them, 2 = mua them mot lan khi
    # RSI(2) van < nguong trong luc dang giu. Bat 27/10/2026 theo yeu cau van
    # hanh. Bang chung YEU: 26 lenh lop 2 (+399 bps, thang 85%), nhin thay sau
    # khi da xem so, chua kiem ngoai mau. Moi lop la them 1R tren CUNG mot ma.
    # Xem docs/rsi2-connors.md § Mua them. Dat qua RSI2_LAYERS trong compose.
    "layers": _i("RSI2_LAYERS", 2),
}
XSMOM = {
    "topn": 20, "lookback": 30, "frac": 0.10, "sleeves": 7, "hold": 7,
    "min_bars": 205, "legs": 2,
    # Loc xu huong: chi MUA neu close > MA, chi BAN neu close < MA.
    # Chot 26/10/2026. Luoi 10/14/20/30/50/100/200 cho CAGR/sut don dinh,
    # cuc dai dung tai 30 — trung cua so cham diem. Xem docs § «Luoi do dai
    # MA». Luu y: KTC cua phan cai thien VAN CHUA LOAI TRU 0; day la lua
    # chon van hanh, khong phai ket luan thong ke.
    "ma": 30,
}
FEE_BPS = 10.0
