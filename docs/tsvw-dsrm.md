# TSVW và DSRM — hai chiến lược khung ngày từ đợt YouTube 2

Bật trong bot ngày 03/11/2026 theo yêu cầu vận hành. Mỗi lệnh 1R (`ALLOC_TSVW`, `ALLOC_DSRM`).
Mã: `app/swing.py`, ghép vào `runner.build_target`.

## Luật (bộ đã chốt, `config.TSVW` / `config.DSRM`)

| | TSVW — "Number One VWAP Day Trading Strategy" (The Secret Mindset, 266.036 view) | DSRM — "Most Effective Stochastic + RSI + MACD Strategy" (Data Trader, 816.894 view) |
|---|---|---|
| Vũ trụ | top 50 thanh khoản (hạng ngày đã đóng) | top 50 |
| Mua | đáy mới 50 nến → close vượt cổ (đỉnh 10 nến trước đáy) trong 10 nến → hồi về cổ (≤ cổ + 0,25 ATR) với VWAP neo tại đáy trong 0,5 ATR quanh cổ → nến xanh close trên cổ (trong 20 nến) | Stoch(14,3,3) K và D < 20 trong 3 nến trước (chưa chạm 80 từ đó) → RSI(14) > 50 **và** MACD(12,26,9) > tín hiệu (nến đầu tiên cả hai đúng) |
| Bán | đối xứng (đỉnh V) | đối xứng |
| Stop | AVWAP − 0,25 ATR(14) | đáy (đỉnh) thấp nhất 10 nến |
| Chốt | 2R tính từ giá khớp | 1,5R |
| Giữ tối đa | 200 ngày | 200 ngày |

Vào lệnh ở lượt 00:05 UTC (= open nến kế tiếp). Một lệnh một mã mỗi chiến lược. Bỏ tín hiệu có stop < 0,1% giá.
Chỉ báo chép nguyên định nghĩa của bản nghiên cứu (ATR/RSI = RMA Wilder từ nến 0, EMA từ x[0]) — **không** dùng `app/indicators.py`.

## Thoát trong bot

- Stop nằm **trên sàn** (dừng an toàn STOP_MARKET, `executor.safety_level`).
- Mỗi lượt chạy kiểm mọi nến đã đóng từ ngày vào: chạm stop → đóng; chạm chốt → đóng; đủ 200 ngày → đóng.
  Chốt khớp ở giá lượt 00:05 hôm sau thay vì đúng mức. Backtest so với chốt trong nến: TSVW +0,478 → +0,472R/lệnh, DSRM +0,255 → +0,248R/lệnh.

## Bằng chứng (scripts/yt_strats2.py, yt_deep2.py, yt_deep2_years.py, yt_deep2_R.py)

- Toàn mẫu 04/2021–10/2026, 1R mỗi lệnh, phí 10 bps + funding:
  - TSVW: 261 lệnh, +0,48R/lệnh, vượt lệnh ngẫu nhiên z 3,43.
  - DSRM: 507 lệnh, +0,25R/lệnh, z 2,33.
- Kiểm độ bền: cả hai qua 6/6 luật viết trước (6 mốc cắt ngày, top 20/100, hai nửa, bỏ 10 lệnh tốt nhất, lưới định nghĩa 83/108 ô ≥ 98% dương).
- Theo năm:
  - TSVW yếu năm 2024 (+0,9R).
  - DSRM yếu năm 2025 (+1,4R).
  - Nửa sau dữ liệu (2024–2026) yếu hơn nửa đầu ở cả hai.
- Ghép vào bot (engine của app, 1R = 1): +809,5R → +1.064,6R, sụt sâu nhất −118,7R → −110,8R, Sharpe 1,18 → 1,50.
- Phát lại từng ngày bằng chính hàm của app (`scripts/swing_replay.py`): TSVW +0,466R/lệnh, DSRM +0,312R/lệnh.
- Khớp tín hiệu với bản nghiên cứu: 100% (`scripts/swing_parity.py`).

**Rủi ro biết trước:** hai chiến lược được chọn sau 709 ô YouTube (54 bộ luật). Bộ gốc TSVW có z 3,43, dưới ngưỡng Šidák 3,89. Đây là lựa chọn vận hành, không phải kết luận thống kê.

## Vận hành

- `RISK_MAX_OPEN` 33 → 63. Backtest có trung bình 12,7 lệnh mở cùng lúc, p95 27, đỉnh 43; vượt thì lệnh mới bị chặn và ghi lý do.
- Ở 1R = 2 USD, cỡ lệnh trung vị là TSVW 15,6 USD và DSRM 10,3 USD. Khoảng 6–8% lệnh rơi dưới mức tối thiểu 5 USD của sàn, bị bỏ qua.
- Tắt: đặt hệ số 1R = 0 trong tab cấu hình. Vị thế đang mở sẽ đóng ở lượt kế tiếp.
- Tab «Tính lịch sử» (`app/backtest.py`) **chưa** mô phỏng hai chiến lược này.
