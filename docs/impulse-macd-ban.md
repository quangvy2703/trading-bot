# Impulse MACD 1D chỉ bán — chiến lược chính từ 06/11/2026

Người dùng yêu cầu đưa Impulse MACD 1D chỉ bán thành chiến lược chính. Trong
UI nó là **PP7 · IMD bán**, khoá `imd`.

## Luật

Áp dụng cho nến 1D đã đóng (cắt 00h UTC), vũ trụ top 50 thanh khoản.

- **Chỉ báo:** Impulse MACD (LazyBear).
  - `hi = RMA(high, 34)`, `lo = RMA(low, 34)`, `mi = ZLEMA(hlc3, 34)`.
  - `md = mi − hi` nếu `mi > hi`; `mi − lo` nếu `mi < lo`; còn lại 0.
  - Đường tín hiệu `sb = SMA(md, 9)`.
  - Mức "cao" `lev = SMA(|md|, 200)` của nến trước.
- **Vào lệnh BÁN** ở open nến kế tiếp, khi cả ba điều kiện cùng đúng:
  - `sb` cắt lên trên `md`;
  - ở nến trước, `md > 2·lev`;
  - ở nến trước, `sb > 2·lev`.
  Bỏ 250 nến đầu của mỗi mã.
- **Stop:** đỉnh cao nhất của 5 nến tính đến nến tín hiệu. Stop đặt trên sàn
  bằng lệnh STOP_MARKET (`executor.safety_level`).
- **Chốt lời:** 10R tính từ giá khớp. Nếu stop xa hơn 10% thì mức chốt ≤ 0, tức
  không bao giờ chạm, và bot bỏ mức chốt.
- **Thời gian giữ:** tối đa 200 ngày. Mỗi mã chỉ có một lệnh IMD tại một thời
  điểm.
- **Cỡ lệnh:** 1R = `RISK_R_USD × ALLOC_IMD`; giá trị lệnh = 1R ÷ khoảng cách
  stop.

**Code:**
- `app/swing.py` (`imd`, `imd_signals`), dùng chung khung với TSVW/DSRM: tín
  hiệu chạy ở lượt 00:05, thoát khi chạm stop / chạm chốt / đủ 200 ngày.
- Tham số khoá trong `config.IMD`.

## Bằng chứng (nghiên cứu cũ, 03/11/2026)

- Bộ tham số m 2 / chốt 10R / stop đỉnh 5 nến được chọn sau lưới 152 ô
  (`scripts/yt_imd_short_grid.py`).
- Qua 6/6 luật sổ giấy:
  - 456 lệnh, +0,56R mỗi lệnh, vượt null +0,61R (z 2,92);
  - 6/6 mốc cắt ngày;
  - hai nửa mẫu đều dương (nửa đầu z 1,29);
  - top 20 và top 100 đều dương.
- Bonferroni trên 152 ô: p ≈ 0,27. Đây là ứng viên, không phải kết luận thống
  kê.
- Lãi R theo năm:

  | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---|---|---|---|---|---|
  | +21 | +58 | −2 | +81 | +66 | +30 |

- Giữ lệnh trung bình 85 ngày (trung vị 37). 32% số lệnh giữ đủ 200 ngày.

## So với bot hiện tại (06/11/2026)

Mốc là bot 6 phương pháp + windfall: lãi 16.336 USD, Sharpe 2,558, sụt 898 USD,
16/67 tháng âm. Không áp trần; KTC 95% tính bằng bootstrap khối 30 ngày.

| ALLOC IMD | Thêm lãi | Sharpe | ΔSharpe (KTC 95%) | Sụt | Tháng âm |
|---|---|---|---|---|---|
| 1 | +507 | 2,571 | +0,013 [−0,06; +0,09] | 938 | 14 |
| **2 (mặc định)** | **+1.014** | **2,558** | **+0,000 [−0,14; +0,14]** | **978** | **15** |
| 3 | +1.521 | 2,523 | −0,034 | 1.017 | 16 |
| 5 | +2.535 | 2,414 | −0,144 [−0,47; +0,17] | 1.097 | 17 |

- Tương quan ngày với các phương pháp khác:

  | Động lượng | RSI(2) | TSVW | DSRM | C13 | VSA |
  |---|---|---|---|---|---|
  | +0,15 | −0,18 | +0,27 | +0,21 | +0,09 | −0,16 |

  Từ khi có TSVW/DSRM, IMD trùng một phần chân bán của chúng, nên lợi ích đa
  dạng hoá nhỏ hơn lúc nghiên cứu (khi đó bot chỉ có Động lượng + RSI(2)).
- **Chọn ALLOC 2:** lãi thêm khoảng 1.000 USD mà Sharpe gần như không đổi. Với
  ALLOC 5 (ngang các phương pháp khác), lãi thêm 2.500 USD nhưng Sharpe giảm và
  sụt sâu hơn 200 USD.

## Phơi nhiễm

Tính trên 1R = 1 USD; nhân với `RISK_R_USD × ALLOC`.

- Phơi nhiễm trung bình 103 USD, p95 232 USD. Ở ALLOC 2 (1R = 4 USD) là trung
  bình ~410 USD, p95 ~930 USD.
- Số lệnh mở cùng lúc: trung bình 19, p95 43, tối đa 50. Vì vậy
  `RISK_MAX_OPEN` nâng từ 63 lên 115.
- Giá trị một lệnh: trung vị 6R, tức 1R ÷ stop trung vị 16,6%.

## Kiểm đã làm

- `scripts/imd_parity.py`: tín hiệu và mức stop của app trùng 100% với bản
  nghiên cứu, trên toàn lịch sử mọi mã từng vào top 50 (468/468).
- `signals_today("imd")` ra đúng 93/93 tín hiệu năm 2026.
- Chạy trọn một lượt trên bản sao DB, chế độ giấy, với tín hiệu giả: lệnh BÁN
  được mở đúng cỡ (4 USD ÷ 12% = 33,3 USD); stop trên sàn = mức stop; mức chốt ≤
  0 thì bỏ.
- `scripts/add_imd_overview.py` thêm phơi nhiễm, số vị thế và thống kê R của
  IMD vào `methods_bt.json`. Chuỗi ngày tái lập đúng `series['imd']`.

## Khác với nghiên cứu

- Nghiên cứu cho phép tín hiệu ngay trên nến thoát lệnh. Bot bỏ mã vừa thoát
  khỏi lượt chạy hôm đó; TSVW/DSRM cũng làm vậy.
- Bot bỏ tín hiệu có stop < 0,1% giá (`MINRISK`). Với stop đỉnh 5 nến điều này
  gần như không xảy ra.
