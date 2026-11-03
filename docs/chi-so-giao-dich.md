# Bộ chỉ số giao dịch đầy đủ của bot — 30/10/2026

Đây là phần **mô tả**, không phải phép thử: đo lại các lệnh của bot bằng mọi
chỉ số phổ biến về đường đi của giá, chất lượng giao dịch, biến động và rủi ro
đuôi. Chỉ phần ước lượng biến động có một phép thử luật (3 ô), ghi ở cuối.

- `scripts/trade_metrics.py`: engine «Tính lịch sử» với cấu hình đang chạy
  (500 USD, 1R = 2 USD, ALLOC 8/1, ba lớp, stop HVN, chặn mua 90 ngày),
  2021-04 → 2026-10, 3.854 lệnh. Đường đi lấy từ high / low nến ngày. Lệnh vào
  ở open và ra ở open, nên stop của engine khớp ở open hôm sau và MAE có thể
  vượt 1R.
- `scripts/vol_estimators.py`: dự báo biến động và phép thử điểm động lượng.

Đơn vị R là `r_usd` của chính từng lệnh: RSI(2) là khoảng tới stop, động
lượng là σ30·√7.

## 1 · Đường đi trong lệnh: MFE, MAE, ETD, thời gian

ETD = MFE − lãi thực (trước phí).

| R, trung vị (p95) | RSI(2) thắng | RSI(2) thua | Động lượng thắng | Động lượng thua |
|---|---|---|---|---|
| MFE | 0,34 (2,18) | 0,11 (0,65) | 1,46 (7,18) | 0,38 (1,60) |
| MAE | 0,12 (0,71) | 0,68 (1,46) | 0,37 (1,36) | 1,14 (3,29) |
| ETD | 0,06 (0,37) | 0,43 (1,69) | 0,62 (3,71) | 1,22 (3,26) |
| Ngày tới MFE | 2 | 0 | 6 | 1 |
| Ngày tới MAE | 0 | 4 | 1 | 6 |

- **RSI(2) thoát rất sát đỉnh.** Lệnh thắng chỉ trả lại 0,06R từ MFE. Lệnh
  thắng đạt MFE vào ngày thứ 2. Lệnh thua thì lên đỉnh ngay ngày vào, rồi trôi
  xuống tới ngày thứ 4. Điều này khớp với phép thử time stop (ra sau 3 ngày
  không hơn mốc), vì lệnh thua vẫn thoát ở RSI > 70.
- **Động lượng trả lại rất nhiều.** Tổng ETD là 4.744R so với lãi gộp +482R.
  Lệnh thắng cần trung vị 6 ngày mới tới MFE và trả lại 0,62R. Con số này *trông
  như* chỗ cần chốt lời, nhưng mọi luật vắt lại phần này đều đã thua: chốt lời,
  stop kéo theo, hoà vốn, stop MAE. Lý do: đuôi phải (p95 MFE 7,2R) nằm trong
  chính những lệnh đó.

## 2 · Chất lượng giao dịch

| | Thắng | AvgWin | AvgLoss | Profit factor | Kỳ vọng / lệnh |
|---|---|---|---|---|---|
| RSI(2) | 71,6% | +0,477R | −0,489R | 2,46 | **+0,203R** |
| Động lượng | 48,0% | +1,268R | −0,910R | 1,29 | **+0,136R** |

Kỳ vọng E = Pw·AvgWin − Pl·AvgLoss, trùng với R trung bình.

Đường vốn theo ngày (USD):

| | Lãi ròng | Sụt max | Run-up max | Sharpe | Sortino | Calmar | Recovery |
|---|---|---|---|---|---|---|---|
| RSI(2) | +572 | 84 | 610 | 1,17 | 2,49 | 1,23 | 6,8 |
| Động lượng | +1.008 | 219 | 1.095 | 0,88 | 1,28 | 0,83 | 4,6 |
| **Cả bot** | **+1.580** | **219** | 1.644 | **1,24** | 1,93 | 1,30 | 7,2 |

Calmar = lãi ròng mỗi năm ÷ sụt max. Recovery = lãi ròng ÷ sụt max. Sortino
cao gần gấp đôi Sharpe ở RSI(2): phần biến động của nó chủ yếu nằm ở phía lời.

## 3 · Đường đi của giá: chạm ngưỡng trước, triple barrier, hiệu quả đường đi

Xác suất chạm +k R trước −k R trong lúc giữ lệnh. Ngày chạm cả hai thì tính là
chạm ngược (mơ hồ ≤ 3,4%).

| k | RSI(2): +k trước | −k trước | không chạm | Động lượng: +k trước | −k trước | không chạm |
|---|---|---|---|---|---|---|
| 0,5 | 22,7% | 28,4% | 48,9% | 49,0% | 47,4% | 3,7% |
| 1,0 | 11,4% | 8,0% | 80,7% | **37,3%** | **32,6%** | 30,2% |
| 1,5 | 8,0% | 1,7% | 90,3% | 25,6% | 17,4% | 57,0% |
| 2,0 | 5,1% | 1,1% | 93,8% | **17,6%** | **9,5%** | 72,8% |

- **Lợi thế của động lượng lộ rõ khi ngưỡng xa.** Ở ±0,5R gần như tung đồng
  xu, ở ±2R thì tỉ lệ là 1,9 : 1. Đây là đuôi phải nhìn theo một cách khác,
  và cũng là lý do lệnh nhồi ±1 ATR có kỳ vọng dương.
- **RSI(2): 81% lệnh không chạm ±1R** trước khi ra, vì stop HVN rộng so với
  cú bật 2–4 ngày.
- Nhãn triple barrier (±1R, rào dọc = ngày ra thật): RSI(2) +1 / 0 / −1 là
  11 / 81 / 8%; động lượng là 37 / 30 / 33%.
- Hiệu quả đường đi (|giá ra − giá vào| ÷ tổng |bước close|), trung vị: RSI(2)
  thắng 0,76 và thua 0,31. Động lượng thắng 0,23 và thua 0,32 (tương quan với
  R −0,11). Lệnh thắng của động lượng đi rất gập ghềnh. Chỉ số này đo sau khi
  ra lệnh nên không dùng được làm tín hiệu.

## 4 · Phân phối và rủi ro đuôi

| R mỗi lệnh | p5 | p25 | p50 | p75 | p95 | VaR 95% | ES 95% | VaR 99% | ES 99% |
|---|---|---|---|---|---|---|---|---|---|
| RSI(2) | −0,96 | −0,04 | +0,13 | +0,34 | +1,67 | −0,96 | −1,34 | −1,43 | −2,10 |
| Động lượng | −1,92 | −0,71 | −0,06 | +0,73 | +2,84 | −1,92 | −3,01 | −3,36 | −5,29 |

Theo ngày, cả bot: VaR 95% −14,6 USD, ES 95% −24,8 USD.

**Monte Carlo** (10.000 năm giả, ghép các khối 30 ngày lãi ngày thật của cả
bot, 1R = 2 USD cố định):

| | p5 | p50 | p95 | p99 |
|---|---|---|---|---|
| Lãi 1 năm (USD) | −71 | +262 | +726 | — |
| Sụt trong năm (USD) | — | 132 | **271** | **351** |

- **10,4% số năm lỗ.**
- **Sụt lịch sử 219 USD bằng 44% vốn đầu 500 USD.** Theo Monte Carlo, một năm
  bất kỳ có 5% khả năng sụt quá 271 USD (54% vốn đầu) và 1% khả năng sụt quá
  351 USD (70%). Với tài khoản đang ở mức 500 USD thì 1R = 2 USD là mạnh tay.
  Nếu đợt sụt rơi vào đầu kỳ chạy thật thì đó là mức này. Đây là cùng lo ngại
  "ALLOC 8 có thể quá tay" đã ghi trước đây.

## 5 · Ước lượng biến động

**Dự báo** biến động thực 7 ngày tới (top 20, mỗi 7 ngày, 5.779 quan sát; mỗi
ước lượng dùng 30 nến):

| Ước lượng | Tương quan log | QLIKE (nhỏ hơn là tốt hơn) |
|---|---|---|
| Close-to-close (đang dùng) | 0,603 | 0,796 |
| **Parkinson** (high/low) | **0,616** | **0,718** |
| Garman–Klass (OHLC) | 0,614 | 0,726 |
| Yang–Zhang (OHLC + khoảng qua đêm) | 0,610 | 0,743 |
| NATR (ATR14 ÷ giá) | 0,609 | 5,78 |
| Độ rộng Bollinger 20 | 0,548 | 1,96 |

Ước lượng dùng high/low dự báo nhỉnh hơn close-to-close (QLIKE giảm khoảng
10%). Yang–Zhang không hơn Garman–Klass vì perp crypto giao dịch 24/7: "khoảng
qua đêm" (open hôm nay so với close hôm qua) gần như bằng 0. QLIKE của NATR và
Bollinger cao vì chúng không cùng thang với độ lệch chuẩn lợi suất, chỉ nên
xem cột tương quan. Bollinger kém nhất vì nó đo độ phân tán của *giá*, không
phải của lợi suất.

**Phép thử luật** (`vol_estimators.py`, 3 ô, KTC Šidák 98,30%): điểm động
lượng = lợi suất 30 ngày ÷ σ, thay σ close-to-close bằng ước lượng dùng
high/low. Mốc tính lại khớp từng số.

| σ | bps/kỳ | Vốn gộp | Sụt | CAGR/sụt | Sharpe | Hiệu bps/kỳ (KTC) | Năm + |
|---|---|---|---|---|---|---|---|
| **Close-to-close (mốc)** | +143,3 | 26,79× | 44,1% | 1,61 | 1,15 | — | — |
| Parkinson | +142,9 | 24,84× | 40,6% | 1,70 | 1,15 | −0,4 [−14,5 ; +16,8] | 4/6 |
| Garman–Klass | +141,8 | 24,49× | 42,3% | 1,63 | 1,16 | −1,5 [−18,7 ; +17,6] | 4/6 |
| Yang–Zhang | +135,8 | 21,55× | 43,5% | 1,50 | 1,13 | −7,5 [−27,2 ; +14,9] | 2/6 |

**Giữ close-to-close.** Parkinson và Garman–Klass ngang mốc, sụt thấp hơn một
chút, nhưng KTC của hiệu chứa 0. Đổi σ gần như không đổi thứ hạng.

Chưa đo: σ còn dùng để **định cỡ lệnh** động lượng (1R = σ·√7). Parkinson dự
báo biến động tốt hơn một chút, nên định cỡ theo nó có thể làm rủi ro mỗi lệnh
đều hơn. Muốn đo thì phải sửa engine «Tính lịch sử»; engine nghiên cứu chia
vốn đều.

## Những gì trong danh sách không chạy thành luật, và vì sao

| Phương pháp | Lý do |
|---|---|
| ETD → thoát khi trả lại x% lợi nhuận đỉnh | Đây chính là stop kéo theo: đã thử, hại động lượng, không kích hoạt ở RSI(2) |
| Thời gian tới MFE → time stop | Đã thử: RSI(2) giữ tối đa 3/5/10 ngày, động lượng các chân trời giữ khác nhau |
| Triple barrier + meta-labeling | Là bộ lọc lệnh lúc vào bằng ML với một nhãn khác. Mọi bộ lọc lúc vào đã thua; khớp cả 12 đặc trưng chỉ giải thích được 4% kết quả. Đổi nhãn không thêm thông tin |
| NATR / độ rộng Bollinger / biến động thực làm bộ lọc chế độ | Đã thử: lọc biến động lúc vào cho RSI(2) (trong 12 bộ lọc), nhắm biến động cho động lượng (hại) |
| Xác suất có điều kiện / xác suất chạm trước | Là bảng ở mục 3. Luật tương ứng (lệnh nhồi ±1 ATR) đã xác nhận |
