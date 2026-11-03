# Các họ chiến lược phổ biến — 30/10/2026, LOẠI CẢ NĂM

Đợt này đi theo một danh sách tổng quan các "trường phái" trading (trend
following, mean reversion, breakout, momentum, pairs, stat-arb, carry, market
making, mô hình chế độ, các phép đánh giá). Phần lớn danh sách **đã thử từ
trước**. Đợt này chỉ chạy những biến thể **chưa có**, cùng kỷ luật cũ: luật
quyết viết trong docstring trước khi chạy, lưới in đủ, chọn vùng ổn định,
null max-over-grid, cộng ô vào kế toán.

## Bản đồ: cái gì đã có, cái gì mới

| Họ trong danh sách | Tình trạng |
|---|---|
| Momentum cắt ngang | **đang chạy** (`xsmom-volnorm.md`) |
| Mean reversion kiểu RSI | **đang chạy** — RSI(2) Connors |
| Trend following: MA crossover, Donchian | đã chết (`screen_families`, 623 mã) |
| Pairs theo tương quan, z-score | đã chết, −44 … −78 bps/lệnh |
| Volatility breakout (Larry Williams) 1H, ORB 15 phút | đã loại (`trong-ngay.md`) |
| Carry funding: cắt ngang / trung hoà spot–perp | 1/6 ô / không đáng mở (`carry-trung-hoa.md`) |
| Volume momentum | sốc khối lượng: trượt Šidák |
| Market making | cần dữ liệu tick / sổ lệnh — chưa có |
| **TSMOM** (Moskowitz–Ooi–Pedersen) | **mới, 8 ô — loại** |
| **Bollinger / z-score reversion** | **mới, 36 ô — loại** |
| **Breakout nến ngày: xác nhận khối lượng, squeeze, Larry Williams ngày** | **mới, 8 ô — loại** |
| **Pairs theo đồng liên kết (Engle–Granger)** | **mới, 8 ô — loại** |
| **HMM hai trạng thái làm công tắc** | **mới, 4 ô — loại** |
| **Deflated Sharpe, chi phí hoà vốn** | **mới, mô tả** |

## 1 · TSMOM — `scripts/tsmom.py`

Mỗi mã tự xét chính nó: lợi suất L ngày > 0 thì mua, < 0 thì bán. Tỷ trọng
rủi ro đều (1/σ30), tái cân bằng 7 ngày, 7 sổ lệch ngày, phí 10 bps trên toàn
danh nghĩa mỗi kỳ, funding thật. Lưới L 30/90/180/365 × top 20/50.

| Ô | bps/kỳ | KTC 99,36% | Vốn | Sụt | Sharpe |
|---|---|---|---|---|---|
| L30 top20 | +57,0 | [−28 ; +147] | 2,79× | 38% | 0,59 |
| **L30 top50 (chọn)** | +51,2 | [−36 ; +138] | 2,55× | 37% | 0,52 |
| L90 | −16,5 / +0,6 | | 0,30× / 0,46× | 72–81% | ≈ 0 |
| L180 | −30,7 / −37,2 | | ≈ 0,2× | 87–90% | −0,3 |
| L365 | −8,7 / −9,9 | | ≈ 0,45× | 63–65% | −0,1 |

**Loại** (✗✓✓✓): KTC chứa 0. Chỉ chân trời 30 ngày sống, và nó tương quan
+0,36…+0,42 với động lượng cắt ngang đang chạy, tức phần lớn là cùng một hiệu
ứng nhưng có thêm phơi nhiễm thị trường. Trộn 50/50 với động lượng **hạ**
Sharpe từ 1,15 xuống 1,05–1,07. Chân trời 3–12 tháng, chính là chân trời của
bài báo gốc, thua trên crypto: xu hướng dài đảo chiều trước khi tín hiệu kịp
lật.

Null đổi chiều ngẫu nhiên cho p = 0,000, nhưng null này yếu: đổi chiều độc
lập từng mã làm mất tương quan chéo nên phương sai null nhỏ hơn thật. Điều
kiện chặn là KTC.

## 2 · Bollinger / z-score reversion — `scripts/bb_revert.py`

Cùng khung với RSI(2): top 10, 5 chỗ, stop HVN, chấm ở 6 cách cắt ngày.
Vào khi z = (close − SMA_N) / sd_N < −k, ra khi z > 0 hoặc > +1, có hoặc không
lọc close > SMA50. Lưới N 5/10/20 × k 1,5/2/2,5 × ra × lọc = 36 ô.

| | Lệnh | R/lệnh | R/năm÷sụt | Sharpe tháng |
|---|---|---|---|---|
| RSI(2) 10/70 (mốc, cùng engine) | 156 | **+0,206** | **1,85** | **1,11** |
| Ô chọn: N20 k2,0 ra>0 MA50 | 41 | −0,019 | −0,04 | −0,09 |
| Ô tốt nhất thô: N20 k1,5 ra>0 MA50 | 120 | +0,064 | 0,36 | 0,55 |
| Ô không lọc (18 ô) | | âm ở 18/18 | | |

**Loại** (✗✗✗✗✗). Không ô nào tới gần RSI(2). Các ô không có lọc xu hướng
âm toàn bộ: bắt dao rơi. Bollinger không trùng lệnh nào với RSI(2), vì
RSI(2) đòi close > MA20 còn z20 < −2 thì gần như luôn dưới MA20. Hai cái đo
hai thứ khác nhau: RSI(2) bắt cú giảm 2 ngày trong xu hướng lên, Bollinger
bắt độ lệch lớn khỏi trung bình 20 ngày, và độ lệch lớn trên crypto thường là
xu hướng đang gãy.

Lỗi lưới: z của nến cuối trong cửa sổ N nến không bao giờ vượt √(N−1), tức 2
với N = 5, nên 8 ô N5 k ≥ 2 rỗng. Vẫn cộng vào kế toán.

## 3 · Breakout nến ngày — `scripts/breakout_daily.py`

Chỉ mua, top 50, một mã một lệnh, null = cùng danh sách tín hiệu nhưng vào ở
nến ngẫu nhiên.

| Ô | Lệnh | bps/lệnh | KTC 99,36% | Null TB | z |
|---|---|---|---|---|---|
| Donchian 20 + khối lượng > 1,5× | 1.025 | +114 | [−599 ; +762] | +82 | +0,21 |
| Donchian 20 + khối lượng > 2,5× | 729 | +168 | [−595 ; +843] | +106 | +0,28 |
| Donchian 55 + khối lượng (2 ô) | 450–532 | −244 … −263 | | +92 … +147 | −0,6 |
| Squeeze (BBW thấp nhất 10% / 20% của 120 ngày) rồi bung | 649 / 884 | +30 / +13 | [−492 ; +652] | +117 | −0,9 / −1,1 |
| Larry Williams ngày, k 0,5 | 34.730 | −3,7 | [−25 ; +17] | −4,8 | +0,35 |
| Larry Williams ngày, k 1,0 | 13.649 | +7,3 | [−19 ; +32] | −4,0 | +2,18 |

**Loại** (✗✗✓✓, null max-over-grid p = 0,995). Breakout giữ dài không hơn
vào ngẫu nhiên rồi giữ cùng luật ra. Phần lời đến từ việc cầm crypto lâu,
không từ điểm vào. Xác nhận khối lượng không cứu được Donchian. Larry Williams
k 1,0 có z +2,18, nhưng sau 8 ô (ngưỡng ≈ 2,7) và với KTC chứa 0 thì chỉ là
nhiễu; bản 1H của nó cũng đã loại.

## 4 · Pairs theo đồng liên kết — `scripts/pairs_coint.py`

Chọn cặp bằng ADF trên phần dư hồi quy log A = a + b·log B (t < −3,37, tối
đa 50 cặp), giao dịch phần dư với hệ số phòng hộ b. Lưới W 90/180 × z vào
2/2,5 × top 50/100.

| | bps/lệnh | KTC |
|---|---|---|
| W90 (4 ô) | −60 … −86 | chứa 0 |
| W180 (4 ô) | −131 … −165 | **loại 0 về phía âm** |
| Null ghép cặp ngẫu nhiên | −183 … −259 | |

**Loại** (✗✓✗✗). Đồng liên kết chọn cặp *tốt hơn* ghép ngẫu nhiên rất rõ
(p = 0,000), nhưng tốt hơn ở chỗ lỗ ít hơn. Trên crypto, chênh lệch giữa hai
mã có xu hướng chứ không quay về, nên đặt cược hồi quy là đứng ngược động
lượng. Đây cũng là kết quả của bản tương quan cũ.

## 5 · HMM làm công tắc chế độ — `scripts/hmm_regime.py`

HMM Gauss hai trạng thái trên lợi suất ngày BTC, Baum–Welch trên cửa sổ mở
rộng, ước lượng lại mỗi 30 ngày, xác suất lọc (không nhìn trước). Trạng thái
"xấu" = phương sai lớn. Dữ liệu BTC perp trong cache bắt đầu 2020-09, cần 450
ngày để ước lượng nên P có từ **2021-12**; năm 2021 không bị tắt.

- P_xấu > 0,5 ở 23% số ngày, nhiều nhất năm 2024 (40%).
- Trạng thái biến động cao **không phải trạng thái giảm**: μ +15 bps/ngày,
  so với +5,5 ở trạng thái êm. Biến động crypto là biến động hai chiều.

| | bps/kỳ hay R/lệnh | Sharpe | Hiệu (KTC 97,47%) | Quyết |
|---|---|---|---|---|
| Động lượng, mốc | +143,3 | 1,15 | | |
| Tắt khi P > 0,5 | +124,8 | 1,05 | −18,5 [−39,7 ; +1,1], 0/6 năm | giữ |
| Tắt khi P > 0,8 | +133,6 | 1,10 | −9,7 [−25,7 ; +3,6] | giữ |
| RSI(2), mốc | +0,206 | 1,24 | | |
| Bỏ tín hiệu khi P > 0,5 | +0,216 | 1,06 | Sharpe −0,60 … +0,07 | giữ |
| Bỏ tín hiệu khi P > 0,8 | +0,210 | 1,09 | Sharpe −0,39 … −0,02 | giữ |

**Loại cả bốn.** Cả hai chiến lược đều có lời trong trạng thái xấu: động
lượng +93 bps/kỳ, RSI(2) +0,200R/lệnh, gần bằng trạng thái êm. Tắt đi là mất
lời. Đây là lần thứ ba một bộ lọc chế độ thua, sau nhắm biến động và tắt chân
bán khi gấu.

## 6 · Deflated Sharpe và chi phí hoà vốn — `scripts/deflated_sharpe.py`

Mô tả, không phải phép thử. Lãi lỗ ngày của engine «Tính lịch sử», cấu hình
đang chạy, 2.028 ngày. SR0 = Sharpe lớn nhất *kỳ vọng* nếu cả N biến thể đều
là nhiễu. DSR = xác suất Sharpe thật > SR0.

| | Sharpe/năm | Lệch | Nhọn | PSR(0) | DSR N=10 | N=50 | N=200 | N đã đếm |
|---|---|---|---|---|---|---|---|---|
| RSI(2) | 1,17 | +5,4 | 71 | 0,999 | 0,92 | 0,71 | 0,49 | 469 → 0,37 |
| Động lượng | 0,88 | −0,9 | 31 | 0,978 | 0,68 | 0,42 | 0,25 | 869 → 0,13 |
| **Cả bot** | **1,24** | +0,1 | 25 | 0,998 | **0,91** | **0,74** | 0,56 | 1.338 → 0,34 |

Đọc bảng này cho đúng:

- **N đã đếm là cận trên quá xa.** Phần lớn số ô là lớp phủ (stop, thoát,
  lọc) thử *trên* một chiến lược đã chọn, không phải chiến lược thay thế; và
  chúng tương quan rất mạnh với nhau. Số lựa chọn thật sự độc lập dẫn tới cấu
  hình đang chạy cỡ vài chục, tương ứng cột N = 10…50.
- **Ở N = 50, cả bot có DSR 0,74.** Đây chưa phải bằng chứng chắc chắn: còn
  khoảng một phần tư khả năng Sharpe 1,24 chủ yếu là may của việc chọn. Động
  lượng một mình yếu hơn (0,42), vì Sharpe ngày của nó chỉ 0,88 và đuôi trái
  dày.
- **V = 1/(T−1) là giả định** (mỗi biến thể là nhiễu thuần). Phương sai
  Sharpe thật giữa các ô không được lưu lại.

Kết luận thực tế: số liệu lịch sử đã vắt hết sức của nó. Thứ duy nhất nâng
được DSR là **dữ liệu mới**, tức sổ giấy hoặc tiền nhỏ chạy tiếp, không phải
thêm phép thử trên cùng 5,5 năm.

**Chi phí hoà vốn** (lãi ròng ÷ tổng danh nghĩa vào + ra):

| | Lệnh | Lãi ròng | Chịu thêm được |
|---|---|---|---|
| RSI(2) | 176 | +572 USD | **148 bps** mỗi chiều |
| Động lượng | 3.678 | +1.003 USD | **80 bps** mỗi chiều |

Phí taker thật cỡ 4–5 bps mỗi chiều, nên phí và trượt giá không phải thứ đe
doạ hai chiến lược này. Động lượng mỏng hơn vì quay vòng nhiều gấp 3 lần.

## Những gì trong danh sách không chạy, và vì sao

| Mục | Lý do |
|---|---|
| Market making | Cần dữ liệu tick và sổ lệnh. 15 phút trước phí đã ≈ 0 (`trong-ngay.md`) |
| Industry momentum | Không có phân loại ngành đáng tin cho 623 mã. Ngành crypto (L1, DeFi, meme…) thay đổi theo mùa |
| Earnings momentum | Crypto không có báo cáo lợi nhuận |
| Reinforcement learning | 5,5 năm nến ngày là khoảng 2.000 quan sát. RL cần hàng triệu bước và sẽ học thuộc lòng. Mô hình học máy đơn giản hơn đã thua (12 đặc trưng giải thích được 4%) |
| Bayesian models | Là cách ước lượng, không phải chiến lược. Phần có ích nhất (co tham số về trước) đã làm gián tiếp bằng chọn vùng ổn định thay vì đỉnh nhọn |
| Walk-forward, OOS, Monte Carlo, bootstrap, độ nhạy tham số, phân tích chế độ | Là phương pháp đánh giá, đã dùng trong mọi phép thử. Monte Carlo ở `chi-so-giao-dich.md` |

## Kế toán

| Nhóm | Số ô | Cộng vào |
|---|---|---|
| TSMOM | 8 | động lượng / cắt ngang |
| Breakout nến ngày | 8 | động lượng / cắt ngang |
| Pairs đồng liên kết | 8 | động lượng / cắt ngang |
| HMM cho động lượng | 2 | động lượng / cắt ngang |
| Bollinger / z-score | 36 | RSI(2) |
| HMM cho RSI(2) | 2 | RSI(2) |

Cắt ngang lên **869 ô**, RSI(2) lên **≈ 469**.
