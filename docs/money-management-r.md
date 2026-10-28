# Quản lý vốn theo đơn vị R — đã chốt

**Ngày chốt:** 26/10/2026 · Áp cho cả [RSI(2)](rsi2-connors.md) và
[động lượng cắt ngang](xsmom-volnorm.md).

Tài liệu này chốt **cách ghi sổ và cách định cỡ lệnh**. Nó không đụng vào tín
hiệu của hai chiến lược.

---

## Vì sao bỏ cách chia 1/N

Cách cũ: mỗi lệnh ăn **1/N vốn hiện tại**. Nó có ba chỗ hỏng.

**1 · Nó không biết lệnh nào rủi ro hơn.** Một lệnh có stop cách 5% và một
lệnh stop cách 40% đều ăn cùng số tiền, trong khi rủi ro thật của chúng lệch
nhau 8 lần.

**2 · Nó trộn lẫn lợi thế với đòn bẩy.** Vốn cuối phụ thuộc vào cả chất lượng
tín hiệu lẫn số tiền đem ra đặt, nên không đọc được riêng phần nào. Đây là
gốc rễ của con số **504×** từng nằm trong `rsi2-connors.md`: luật đếm chỗ cũ
cho phép hơn N vị thế mở cùng lúc, tức âm thầm chạy đòn bẩy, và vũ trụ càng
rộng thì sai số càng phình. Số đúng là **8,30×**.

**3 · Mức rủi ro bị khoá cứng vào N.** Muốn giảm rủi ro phải tăng số chỗ, mà
tăng số chỗ lại đổi luôn cả danh mục.

## Định nghĩa

```
R      = khoảng cách tới điểm thua định trước, tính theo tỷ lệ giá
1R     = 100 USD   ← CỐ ĐỊNH, không đổi theo vốn
cỡ     = 100 / R                        ← R càng nhỏ, mua càng nhiều
lãi/lỗ = 100 × (lợi suất ròng / R)
```

**1R là một số USD cố định, không phải phần trăm vốn.** Hệ quả: lợi nhuận là
phép **cộng**, không gộp lãi; và **vốn không quyết định cỡ lệnh** — nó chỉ
quyết định **mở được bao nhiêu lệnh cùng lúc**. Muốn mở nhiều hơn thì tăng
vốn, chứ không phải đặt cược to hơn.

Bản theo **% vốn** (gộp lãi) đã thử và vẫn đọc được ở § cuối, nhưng không
phải bản chốt: nó trộn lẫn lợi thế với quy mô tài khoản, đúng cái tật đã đẻ
ra con số 504×.

Lợi suất ròng **đã trừ phí và funding**, nên chi phí cũng được quy về R. Đây
là chỗ quan trọng: 10 bps phí trên một lệnh stop 40% chỉ tốn 0,025R, nhưng
cùng 10 bps trên lệnh stop 2% tốn 0,05R — gấp đôi. Cách chia 1/N che mất điều
này.

**Mẫu số R lấy ở đâu** — khác nhau theo chiến lược, vì cấu trúc rủi ro khác
nhau:

| chiến lược | R | lý do |
|---|---|---|
| RSI(2) | `(giá vào − stop) / giá vào` | có stop thật, R là khoảng cách tới nó |
| động lượng | `σ(log, 30 ngày) × √7` | không có stop; 1R = một lần độ lệch chuẩn bất lợi qua đúng kỳ nắm giữ |

Mẫu số của động lượng **không phải luật mới**: σ chính là mẫu số chiến lược
đã dùng để chấm điểm.

## Hai trần bắt buộc

```
cỡ một lệnh        ≤ 25% vốn
tổng rủi ro đang mở ≤ 5 × risk%
```

Trần thứ nhất **không phải đề phòng suông**. Chạy RSI(2) trên toàn vũ trụ
không chặn gì, đỉnh đòn bẩy **9,78×** đến từ **một lệnh duy nhất**:

```
2026-05-10 · 8 vị thế mở
  USDCUSDT    stop cách  0,05%  →  cỡ 962,8% vốn
  7 lệnh khác stop cách 40,00%  →  cỡ   1,2% vốn mỗi lệnh
```

`USDCUSDT` là perp của một stablecoin neo giá USD: ATR gần bằng 0 nên
`6×ATR` ra stop cách 0,05%, và định cỡ theo rủi ro đòi mua gần 10 lần tài
khoản để cược đúng 0,5%. Không có trần này thì ở mức 3% mỗi lệnh **tài khoản
cháy** — vốn xuống âm.

Trần thứ hai thay cho khái niệm "N chỗ", vốn vô nghĩa khi mỗi lệnh một cỡ.

### Trong bot: trần tính bằng USD

Bot không chặn theo % vốn mà theo hai con số USD, áp trước khi gửi lệnh:
`MAX_ORDER_USD` cho một lệnh và `MAX_GROSS_USD` cho tổng phần mở thêm mỗi lượt.
Từ 28/10/2026 (tài khoản test 500 USD, 1R = 2), hai con số là **500 / 1.500**.
Lý do là stop HVN của RSI(2) có khi chỉ cách giá 2%, nên ở 1R × 8 = 16 USD
lệnh lên tới ~800 USD.

- Lệnh **RSI(2)** vượt `MAX_ORDER_USD` được **thu nhỏ về đúng trần**. Rủi ro
  thực khi đó < 1R, lý do lệnh ghi «thu về trần … R». Lệnh không bị bỏ, vì
  stop gần không phải dấu hiệu lệnh xấu ([stop-dinh-day.md](stop-dinh-day.md)).
- Lệnh **động lượng** vượt trần vẫn bị chặn như cũ.
- Lệnh **đóng** không bao giờ bị chặn.

Quy tắc chọn trần khi đổi 1R vẫn là `MAX_ORDER ≈ 25 × 1R × hệ số`, kiểm lại bằng
tab «Tính lịch sử» (cột «bị chặn»).

## Phụ lục — bản theo % vốn (đã thử, không chốt)

Vặn risk% thì lợi nhuận và sụt đi lên cùng nhịp, tỷ lệ gần như bất biến:

| risk%/lệnh | vốn | sụt | CAGR/sụt |
|---|---|---|---|
| 0,5% | 1,07× | 1,3% | 0,99 |
| 1% | 1,15× | 2,6% | 0,99 |
| 2% | 1,32× | 5,1% | 1,00 |
| 3% | 1,50× | 7,7% | 1,01 |
| 5% | 1,94× | 12,7% | 1,01 |
| **7%** | **2,46×** | **17,8%** | **1,00** |
| 10% | 3,24× | 25,3% | 0,95 |

*(RSI(2), top 10, đánh giá lại theo ngày)*

Vì tỷ lệ không đổi, **risk% không được chọn bằng backtest** — nó là câu hỏi
"chịu được sụt bao nhiêu". Nên nó **không cộng ô nào** vào kế toán đa phép
thử. Mức **7%** tái tạo đúng mức sụt của bản chia 1/N cũ (17,8% so với 18,9%),
dùng làm mốc đối chiếu.

Bản này **không được chốt**: gộp lãi làm vốn cuối phụ thuộc cả vào quy mô tài
khoản lẫn chất lượng tín hiệu, nên không đọc riêng được phần nào. Giữ lại để
đối chiếu.

Ở **10%** tỷ lệ bắt đầu tụt (0,95) — đó là trần đòn bẩy, vượt qua thì vặn
thêm rủi ro chỉ mua thêm sụt.

## R dùng để ghi sổ cho cả hai, nhưng chỉ định cỡ cho RSI(2)

Đã thử áp định cỡ theo R cho động lượng (trọng số nghịch biến động). Nó **kém
hơn chia đều**:

| phân bổ | vốn gộp | sụt | phơi nhiễm TB | CAGR/sụt |
|---|---|---|---|---|
| **chia đều** | **21,49×** | 45,7% | 1,00× | **1,43** |
| rủi ro 1% | 1,86× | 15,0% | 0,32× | 0,71 |
| rủi ro 3% | 5,76× | 30,2% | 0,77× | 1,10 |
| rủi ro 8% | 13,64× | 47,2% | 0,97× | 1,13 |

Cột cuối tăng đơn điệu khi vặn rủi ro lên, và lý do nằm ở trần 25%: risk%
càng cao thì càng nhiều vị thế chạm trần, mà **bốn vị thế cùng chạm trần 25%
chính là chia đều**. Dữ liệu đang nói "càng giống chia đều càng tốt".

Nguyên nhân: chiến lược **đã chia cho σ ngay ở bước chấm điểm**. Lấy σ làm
trọng số lần nữa là tính hai lần, và nó kéo danh mục về nhóm biến động thấp —
trong crypto là nhóm vốn hoá lớn, nhóm trả ít động lượng nhất.

**Nên: động lượng giữ chia đều.** R ở đó chỉ là thước đo.

Một ghi nhận ngược chiều, để không bỏ sót: định cỡ theo rủi ro **êm hơn trong
năm xấu**. Năm 2022 chia đều ra 0,75× với sụt 41,0%, còn rủi ro 3% ra 0,98×
với sụt 23,9%. Ai ưu tiên ngủ ngon hơn là ưu tiên vốn cuối thì đây là đánh
đổi có thật — nhưng đổi bằng cách hạ phơi nhiễm của bản chia đều xuống còn
rẻ hơn.

## Kết quả — 1R = 100 USD, vốn ôm 100%

Mỗi vị thế rủi ro đúng 100 USD. Lãi cộng dồn, không gộp.

**RSI(2) · top 10** — vốn cần: đỉnh phơi nhiễm **2.036 USD**

| năm | vị thế | lãi USD | = R | sụt trong năm | phơi nhiễm TB |
|---|---|---|---|---|---|
| 2021¹ | 28 | +270 | +2,7 | 50 | 110 |
| 2022 | 30 | +70 | +0,7 | 186 | 99 |
| 2023 | 24 | +257 | +2,6 | 78 | 79 |
| 2024 | 37 | +218 | +2,2 | 169 | 132 |
| 2025 | 25 | +392 | +3,9 | 52 | 60 |
| 2026¹ | 32 | +261 | +2,6 | 51 | 118 |
| **tổng** | **176** | **+1.468** | **+14,7** | **186** | — |

**RSI(2) · toàn vũ trụ** — vốn cần: đỉnh **37.066 USD**, tối đa **144 vị thế**

| năm | vị thế | lãi USD | = R | sụt trong năm | phơi nhiễm TB |
|---|---|---|---|---|---|
| 2021¹ | 150 | +1.497 | +15,0 | 504 | 461 |
| 2022 | 206 | **−153** | −1,5 | 1.495 | 831 |
| 2023 | 315 | +3.672 | +36,7 | 1.062 | 882 |
| 2024 | 636 | **−2.859** | −28,6 | **5.121** | 2.391 |
| 2025 | 589 | +6.115 | +61,2 | 1.088 | 1.740 |
| 2026¹ | 1.030 | +5.753 | +57,5 | 1.883 | 3.712 |
| **tổng** | **2.926** | **+14.025** | **+140,3** | **5.677** | — |

**Động lượng · 7 sổ** — vốn cần: đỉnh **47.010 USD**, luôn giữ **28 vị thế**

| năm | vị thế | lãi USD | = R | sụt trong năm | phơi nhiễm TB |
|---|---|---|---|---|---|
| 2021¹ | 1.072 | **+14.548** | +145,5 | 5.021 | 16.060 |
| 2022 | 1.460 | **−1.208** | −12,1 | 7.345 | 19.562 |
| 2023 | 1.460 | +6.479 | +64,8 | **9.587** | 27.800 |
| 2024 | 1.464 | **+21.998** | +220,0 | 2.919 | 22.322 |
| 2025 | 1.460 | +5.804 | +58,0 | 2.862 | 21.718 |
| 2026¹ | 1.160 | **−1.015** | −10,2 | 7.333 | 25.173 |
| **tổng** | **8.076** | **+46.605** | **+466,1** | **9.587** | — |

¹ Năm cụt — cả ba bắt đầu ~19/04/2021 (cần 205 nến lịch sử).

**Lợi nhuận tập trung kinh khủng.** Động lượng: 2021 và 2024 góp 36.546 trên
46.605, tức **78% đến từ 2 trên 6 năm**. RSI(2) toàn vũ trụ: 2025+2026 góp
**85%**. Chỉ RSI(2) top 10 là đều — sáu năm dương — nhưng quy mô chỉ
**268 USD/năm**: nó ổn định vì nó bé, không phải vì nó khoẻ.

## Vốn bao nhiêu thì nhận được bao nhiêu

Duyệt lệnh theo thời gian, lệnh nào mở ra mà vượt vốn còn lại thì bỏ.

| vốn | RSI(2) top 10 | RSI(2) toàn vũ trụ | Động lượng |
|---|---|---|---|
| 1.000 | 84% · +1.042 | — | — |
| 5.000 | 100% · +1.468 | 57% · +5.071 | 31% · +22.113 |
| 10.000 | 100% | 73% · +5.599 | 52% · +33.559 |
| **20.000** | 100% | 88% · +9.582 | **84% · +47.784** |
| 50.000 | 100% | 99% · +13.692 | 100% · +46.986 |
| 100.000 | 100% | 100% · +14.025 | 100% · +46.605 |

Chỗ 20.000 USD của động lượng ra lãi nhỉnh hơn bản không chặn là **nhiễu** —
nó tình cờ bỏ qua vài vị thế lỗ. Đừng đọc thành mẹo.

**Phơi nhiễm là giá trị hợp đồng, chưa tính đòn bẩy.** Chạy futures 5× thì ký
quỹ còn 1/5, nhưng **sụt vẫn trả bằng tiền thật**: động lượng sụt sâu nhất
9.587 USD, gần một nửa tài khoản 20.000. Vốn phải đủ cho cả hai việc.

**Đỉnh phơi nhiễm rơi vào lúc thị trường êm nhất**, không phải lúc bão — vì
`cỡ = 100 / R` và R của động lượng là σ. Biến động giảm một nửa thì cỡ lệnh
gấp đôi. Đó cũng là lúc rủi ro chế độ cao nhất: đang cầm lượng hàng lớn nhất
với giả định σ cũ, ngay trước khi σ cũ hết hiệu lực.

## Bật / tắt một chiến lược

Vì không còn chia vốn, "phân bổ 50/50" mất nghĩa. Thay bằng **hệ số nhân cho
1R** của từng chiến lược; **0 là tắt**, và tắt thì vị thế đang mở của chiến
lược đó **bị đóng** ở lượt kế tiếp chứ không bị bỏ rơi.

## R không thay được mọi thứ

**R tổng mù với tính đồng thời.** Nó cộng từng lệnh như thể chúng độc lập.
Chạy RSI(2) toàn vũ trụ cho **+137,5R**, gấp 10 lần top 10 (**+13,9R**),
nhưng CAGR/sụt chỉ **0,42–0,44** so với **1,00** — vì hàng chục vị thế mở
cùng một nhịp thị trường, lỗ của chúng chồng lên nhau.

Dùng R để so **chất lượng mỗi lệnh**. Dùng CAGR/sụt để so **danh mục**.

## So hai chiến lược trên cùng thang R

| | R trung bình | thắng | R tổng | số vị thế |
|---|---|---|---|---|
| RSI(2) top 10 | **+0,081** | **73,7%** | +13,9 | 171 |
| Động lượng cắt ngang | +0,058 | 50,1% | **+466** | 8.076 |

Hai cơ chế kiếm tiền khác hẳn nhau: RSI(2) thắng thường xuyên với biên mỏng
(không lệnh nào đạt nổi +1R trong 5,5 năm); động lượng thắng đúng một nửa số
lần nhưng lần thắng lớn hơn lần thua. Chỉ thang R mới cho thấy điều đó.

## Ghép hai chiến lược — hệ số 1R của RSI(2) (27/10/2026)

Ở cùng 1R = 100 USD hai chiến lược **không cùng cỡ rủi ro**: RSI(2) đánh giá
lại theo ngày sụt tối đa ~283 USD, động lượng ~11.259 USD. Chia 1R đều nghĩa
là RSI(2) gần như không có mặt trong danh mục.

**Luật, đăng ký trước:** hệ số không chọn bằng cách nhìn bảng. Cân rủi ro
nghịch biến động, ước **chỉ trên nửa trước 2024-07**:
`k* = σ(lãi/lỗ ngày động lượng) / σ(lãi/lỗ ngày RSI(2))` = **31,9**. Đổi khi
(1) lãi/sụt của bản ghép hơn động lượng ở **cả hai nửa** và (2) tương quan
lãi/lỗ tuần < 0,3 ở cả hai nửa.

Mọi số dưới đây **đánh giá lại theo ngày** (mark to market), không ghi vào
ngày đóng lệnh — bản ghi theo ngày đóng báo thấp sụt của RSI(2).

```
tương quan lãi/lỗ tuần   toàn mẫu +0,028 · < 2024-07 −0,010 · ≥ 2024-07 +0,181
```

| | giai đoạn | lãi USD | sụt USD | lãi/sụt | âm dài nhất |
|---|---|---|---|---|---|
| chỉ động lượng | toàn mẫu | 48.939 | 11.259 | 4,35 | 260 ngày |
| | < 2024-07 | 33.169 | 11.259 | 2,95 | 260 |
| | ≥ 2024-07 | 15.769 | 8.969 | 1,76 | 194 |
| RSI(2) × 32 riêng | toàn mẫu | 46.774 | 9.071 | 5,16 | 342 |
| **ghép (RSI(2) × 32)** | **toàn mẫu** | **95.713** | **11.018** | **8,69** | **142** |
| | < 2024-07 | 48.166 | 11.018 | 4,37 | 142 |
| | ≥ 2024-07 | 47.547 | 7.555 | 6,29 | 138 |

**Đạt cả hai điều kiện.** Lãi gần gấp đôi, sụt **không tăng** (11.018 so với
11.259), đợt âm dài nhất rút từ 260 xuống 142 ngày. Theo năm:

| năm | động lượng | RSI(2) × 32 | ghép |
|---|---|---|---|
| 2021 | 15.246 | 8.761 | 24.007 |
| 2022 | **−499** | 2.077 | **1.579** |
| 2023 | 6.536 | 7.465 | 14.001 |
| 2024 | 21.879 | 7.666 | 29.545 |
| 2025 | 7.409 | 12.491 | 19.900 |
| 2026 | **−1.632** | 8.314 | **6.682** |

Hai năm động lượng âm (2022, 2026) đều được RSI(2) gánh. Lý do cơ học: RSI(2)
chỉ mua khi `close > MA20` nên năm gấu nó **đứng ngoài**, còn động lượng thì
luôn ôm 28 vị thế.

**Ba điều phải nói trước khi đổi cấu hình:**

1. **Đây là đặt cược 32 lần lớn hơn vào 176 lệnh.** RSI(2) × 32 riêng sụt
   9.071 USD — ngang động lượng. Nếu lợi thế RSI(2) là ảo, danh mục vừa thêm
   một nguồn lỗ cỡ động lượng. RSI(2) **chưa có quan sát ngoài mẫu nào**
   (xem `rsi2-connors.md` § Điều này chưa chứng minh). Nửa ≥ 2024-07 đã bị
   nhìn cho hai biến thể động lượng, nên không phải mẫu sạch.
2. **Đợt âm "dài nhất" ở đây đo trên lãi/lỗ cộng dồn USD** (1R cố định),
   không phải đường vốn gộp lãi như `xsmom-volnorm.md` — hai con số 260 và
   493 ngày không so trực tiếp được.
3. **Vốn là thứ bị chặn, không phải rủi ro.** Phơi nhiễm hợp đồng đỉnh ở
   1R = 100 USD: động lượng 44.796, RSI(2) × 32 là 64.843, ghép 73.072. Ở
   1R = 2 USD của app: ghép đỉnh **~1.461 USD**, một lệnh RSI(2) trung vị
   **~159 USD** — vượt `MAX_GROSS_USD = 500` và `MAX_ORDER_USD = 50` mặc định
   trong `docker-compose.yml`. Bản thân động lượng ở 1R = 2 đã đỉnh ~896 USD.

Script: `scripts/combo_rsi2_xsmom.py`.

### SỬA cùng ngày — RSI(2) bị đếm trùng, số ở trên phóng đại

Tab «Tính lịch sử» của app (mô phỏng đúng cơ chế bot) lật ra một lỗi trong
`rsi2_universe.trades()`: vòng lặp **không bỏ qua tín hiệu khi mã đang có
lệnh mở**, nên hai ngày RSI(2) < 10 liên tiếp sinh hai lệnh chồng lên cùng
một mã. Bot thật thì không (`open_syms` loại mã đang giữ).

```
top 10, 1R = 100   tổng 176 lệnh · chồng lấn trên cùng mã 33 (19%)
                   lãi 1.468 USD → bỏ chồng lấn 1.030 USD   (−30%)
```

Đo lại bằng engine của app (khớp thoát ở open hôm sau, không lệnh trùng,
động lượng giữ vị thế trùng không mua bán lại), 1R = 100, không trần:

| `ALLOC_RSI2` | lãi USD | sụt USD | lãi/sụt | âm dài nhất | 2022 |
|---|---|---|---|---|---|
| 0 | 53.291 | 10.943 | 4,87 | 360 ngày | −1.490 |
| 1 | 54.181 | 10.935 | 4,95 | 360 | −1.581 |
| **8** | **60.663** | **10.882** | **5,57** | 361 | −2.219 |
| 16 | 68.071 | 10.931 | 6,23 | 363 | −2.948 |
| 39 (k* mới) | 89.369 | **13.601** | 6,57 | 369 | −5.045 |

```
tương quan lãi/lỗ tuần   < 2024-07 +0,109 · ≥ 2024-07 +0,244
k* = σ(ĐL) / σ(RSI2) trên nửa trước = 39,2
```

**Ba kết luận ở trên phải rút lại:**

1. **"RSI(2) gánh năm 2022" — sai.** Không đếm trùng thì RSI(2) **lỗ** năm
   2022 (−91 USD ở 1R = 100), nên tăng hệ số làm 2022 tệ hơn, không tốt hơn.
   2026 thì vẫn đúng: RSI(2) lãi khi động lượng chững.
2. **"Sụt không tăng ở hệ số 32" — sai.** Ở k* = 39 sụt lên 13.601 (+24%).
3. **"Đợt âm rút từ 260 xuống 142 ngày" — sai.** Đợt âm gần như đứng yên.

**Điều còn đứng:** hai chiến lược vẫn gần như độc lập, và đến hệ số 16 sụt
**không đổi** trong khi lãi tăng (+12% ở ×8, +26% ở ×16). Hệ số **8 đang
chạy vẫn hợp lý**; lý lẽ cho 32 thì không còn.

Bảng `rsi2-connors.md` (176 lệnh, +301,5 bps/lệnh) cũng chứa 33 lệnh trùng
này — **chưa dựng lại**.

## Đổi cỡ lệnh theo thời gian — đã thử 27/10/2026, LOẠI cả ba

Câu hỏi: không đổi tín hiệu, chỉ đổi **1R của lệnh mới** theo diễn biến gần
đây — có làm danh mục đang chạy tốt hơn không? Chạy trên engine của tab
«Tính lịch sử» (hệ số tính từ đường vốn đến close hôm trước, chỉ nhân vào
lệnh mới — đúng cái bot làm được). 1R = 100, không trần, ALLOC 8/1,
`rsi2.layers` = 3, 2021-04-07 → 2026-10-25.

Luật đăng ký trước, quyết trên **toàn bộ thời gian**: (a) KTC 98,3% của
chênh Sharpe > 0 (bootstrap cặp, block 30 ngày, Bonferroni 3 ô), (b) lãi
năm/sụt tăng, (c) Sharpe tốt hơn ≥ 4/6 năm, (d) hai lân cận tham số cũng
tốt hơn.

| | lãi USD | sụt USD | lãi/sụt | Sharpe | chênh Sharpe KTC98 | năm tốt | lân cận | |
|---|---|---|---|---|---|---|---|---|
| **gốc** | 63.812 | 10.882 | 1,06 | **1,06** | | | | |
| V1 nhắm biến động động lượng, 63n | 46.397 | 10.962 | 0,76 | 0,79 | **[−0,59 ; −0,02]** | 1/6 | 42n 1,00 · 126n 0,86 | ✗✗✗✗ |
| V2 nhắm biến động cả danh mục, 63n | 44.594 | 11.305 | 0,71 | 0,75 | **[−0,67 ; −0,03]** | 1/6 | 0,99 · 0,83 | ✗✗✗✗ |
| V3 lọc đường vốn (dưới SMA50 → ½R) | 47.715 | **7.406** | 1,16 | 1,05 | [−0,27 ; +0,24] | 3/6 | 30n 0,98 · 100n 1,03 | ✗✓✗✗ |

V1/V2: hệ số = clip(σ* / σ₆₃, 0,25, 2), σ* là trung vị nhân quả của σ₆₃.
Hệ số trung bình đúng **1,00** (p10 0,67 · p90 1,30), nên đây là so ở **cùng
phơi nhiễm trung bình** — chênh lệch là do *thời điểm*.

**Nhắm biến động không chỉ vô ích mà có hại có ý nghĩa** — ngược với cổ
phiếu, nơi Barroso & Santa-Clara (2015) thấy nó gần gấp đôi Sharpe của động
lượng. Phép giả xác nhận: giữ nguyên chuỗi hệ số của V1 nhưng dịch lệch thời
gian 365 / 730 / 1.095 ngày cho Sharpe 1,04 / 0,88 / 1,06 — đều hơn 0,79.
Cái hại đến từ việc **giảm cỡ đúng lúc động lượng crypto kiếm tiền**: lợi
thế ở đuôi phải (xem `xsmom-volnorm.md` § Frog-in-the-pan), và đuôi đó đến
trong giai đoạn biến động cao. Ý tưởng ngược lại (tăng cỡ khi biến động
cao) là nhìn sau, chưa thử.

V3 cắt sụt 32% nhưng cắt lãi 25% — Sharpe đứng yên, tức nó chỉ là **hạ
phơi nhiễm trung bình** đội lốt quản lý rủi ro. Muốn sụt thấp hơn thì hạ
`RISK_R_USD` cho rẻ hơn.

### Lãi kép — phép tính, không phải phép thử

1R tỉ lệ với vốn, cập nhật mỗi ngày, so với 1R cố định (cùng engine):

| vốn đầu | | vốn cuối | CAGR | sụt |
|---|---|---|---|---|
| 300R | 1R cố định | ×3,13 | 22,8% | 21,5% |
| 300R | lãi kép | ×6,24 | 39,1% | 32,3% |
| 150R | 1R cố định | ×5,25 | 34,8% | 30,6% |
| 150R | lãi kép | ×23,10 | 76,1% | 58,6% |

Ở **cùng mức sụt ~31%**, lãi kép từ 300R cho 39,1%/năm so với 34,8% của 1R
cố định từ 150R — lãi kép nhỉnh hơn một chút, không phải phép màu. Đổi lại
sụt tính theo % lớn dần theo vốn. Cách làm thực tế cho bot: **định kỳ đặt
lại `RISK_R_USD` = vốn / 300** (ví dụ mỗi tháng), không cần code mới.

Script: `scripts/mm_overlay.py`. Engine nhận thêm khoá `rmult` (chỉ dùng
cho nghiên cứu, không có trên UI).

## Tệp

| | |
|---|---|
| `scripts/fixed_r_usd.py` | **Bản chốt** — 1R = 100 USD, cả hai chiến lược, quét vốn |
| `scripts/rsi2_risk_unit.py` | RSI(2) theo R, quét mức rủi ro, theo vũ trụ |
| `scripts/rsi2_all_nocap.py` | Toàn vũ trụ không chặn vốn — hồ sơ đòn bẩy |
| `scripts/xsmom_risk_unit.py` | Động lượng: chia đều so với nghịch biến động |
| `scripts/rsi2_topn_recheck.py` | Dựng lại bảng top N, đối chiếu luật chỗ cũ |
| `scripts/dvt_window.py` | Cửa sổ thanh khoản 30 so với 10 ngày |
| `scripts/combo_rsi2_xsmom.py` | Ghép hai chiến lược, đánh giá lại theo ngày, hệ số cân rủi ro |
| `scripts/mm_overlay.py` | Đổi cỡ lệnh theo thời gian (nhắm biến động, lọc đường vốn) + lãi kép — loại |
| `trading-bot/app/backtest.py` | Engine tab «Tính lịch sử»: mô phỏng đúng bot, kể cả stop HVN và thu lệnh về trần |
