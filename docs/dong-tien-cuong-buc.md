# Dòng tiền cưỡng bức — vị thế đám đông có báo trước giá không?

**Ngày chạy:** 28/09/2026 · **Dữ liệu:** kho `metrics` của Binance USDS-M,
11 symbol, lưới 5 phút, ~5,2 triệu nhịp, 1.161–2.053 ngày mỗi symbol.

Đây là dữ liệu đầu tiên trong cả chuỗi nghiên cứu này mô tả **người** chứ không
mô tả **giá**: bao nhiêu hợp đồng đang treo, và ai đang đứng bên nào.

## Câu hỏi

Khi OI cao **và** vị thế lệch hẳn về một phía, giá có chạy **ngược** phía đám
đông không? Đó là giả thiết nhiên liệu thanh lý: đám đông dồn một phía buộc
phải đóng lệnh khi giá đi ngược, và việc bị ép đó là thứ giá chưa phản ánh.

## Thiết kế (khai báo trước khi chạy lần đầu)

Toàn bộ đường ống **chỉ đọc quá khứ**:

| Bước | Cách làm |
|---|---|
| Bỏ xu hướng chậm | `log(x)` trừ trung bình trượt **30 ngày** của chính nó |
| Xếp hạng | phân vị trong **90 ngày trước đó**, tính riêng từng nhịp |
| Vào lệnh | trễ **1 nhịp 5 phút** sau khi đọc tín hiệu |
| Kết quả đo | log return tới `t+H`, mẫu **không chồng lấn** (stride = H) |

Thước đo vị thế (4 cái, đều tính vào bội số kiểm định):

- `count_long_short_ratio` — tỉ lệ **tài khoản toàn sàn** long/short
- `count_toptrader_long_short_ratio` — tỉ lệ tài khoản top trader
- `sum_toptrader_long_short_ratio` — tỉ lệ **vị thế** top trader
- `sum_taker_long_short_vol_ratio` — tỉ lệ khối lượng taker mua/bán

Thống kê chính: **chênh ép vị thế** `S = TB(r | đám đông Q1) − TB(r | đám đông
Q5)`, tính riêng trong ô OI Q5. Đám đông sai ⟺ `S > 0`.

Kiểm soát: đối chứng dịch 7 ngày · bootstrap block 7 ngày lịch · null
max-over-N bằng dịch vòng tròn ≥ 30 ngày · phí 10 bps khứ hồi.

## Bẫy đã sập và cách gỡ

Bản đầu tiên xếp phân vị trên **toàn mẫu**, không bỏ xu hướng. Đối chứng dịch
7 ngày khi đó cho `+31 bps` — gần một nửa hiệu ứng thật. Cả OI, tỉ lệ vị thế
lẫn giá đều có xu hướng nhiều năm; hai chuỗi cùng trôi theo thời gian tự sinh
ra quan hệ trong bảng dù chúng không liên quan gì nhau ở thang đo ngày.

Trung bình trượt 30 ngày gỡ đúng phần đó. Sau khi gỡ, null riêng cho từng
thống kê có **trung bình ≈ 0** (−0,2 bps trên 500 lần dịch), tức mốc so sánh
đúng là 0 — con số `+31` chỉ là một lần rút nằm gọn trong dải nhiễu
`[−42,7 ; +35,5]`.

## Kết quả

Bảng dưới là bản **nhân quả hoàn toàn** (phân vị trượt 90 ngày, vào lệnh trễ
1 nhịp). `count_long_short_ratio` là thước đo duy nhất sống sót.

| Khung | P&L/lệnh | Cắt đuôi 1% | Thắng | Phí | **Ròng** | n lệnh | Độ phủ | p |
|---|---|---|---|---|---|---|---|---|
| 4h | +7,85 bps | +4,57 | 48,6% | 10 | **−2,2 bps** | 11.160 | 9/11 | <0,002 |
| 1 ngày | +39,03 bps | +25,92 | 49,1% | 10 | **+29,0 bps** | 1.802 | 8/11 | <0,002 |

Khung 1h cũng có ý nghĩa thống kê (p < 0,0001) nhưng chỉ `+2,0…+4,1 bps` mỗi
lệnh — **dưới phí**, nên vô dụng.

### Khung 1 ngày, mổ xẻ

- **Mọi năm đều dương:** 2022 `+38,97` · 2023 `+29,65` · 2024 `+64,71` ·
  2025 `+27,76` · 2026 `+13,94` bps mỗi lệnh. Xu hướng giảm dần rõ rệt.
- **Bỏ từng symbol một:** `+31,6` … `+44,2` bps, không lần nào về gần 0 —
  không phải chuyện của một đồng.
- **Cắt cả 1% cao nhất lẫn 1% thấp nhất:** vẫn `+25,92 bps`, tức lợi thế không
  nằm hết ở vài cây nến.
- **Tỉ lệ thắng 49,1%** với trung bình dương: toàn bộ lợi thế nằm ở việc lệnh
  thắng **to hơn** lệnh thua, đúng hình dạng của một cú ép vị thế.
- **CI 95%** (bootstrap block 7 ngày) cho `S`: `[+23,2 ; +133,6]` bps.
- **Null** (500 lần dịch vòng tròn chuỗi lợi nhuận ≥ 30 ngày): trung bình
  `−0,2`, p95 `|.|` `48,4`, thực tế `+77,79` → p hai phía `< 0,002`.
- Tần suất: ~360 lệnh/năm trên cả 11 symbol, tức ~33 lệnh/symbol/năm.

## Điều này chưa chứng minh

1. **Cơ chế chưa xác định.** Khi đám đông dồn long, perp thường giao dịch cao
   hơn spot và basis co lại. Kết quả đo được có thể là cú ép vị thế, có thể
   chỉ là basis co — hai thứ này chưa tách được bằng dữ liệu ở đây.
2. **Funding chưa tính vào.** Short khi đám đông long là **nhận** funding, nên
   con số ròng ở trên là ước lượng thận trọng theo chiều có lợi cho chiến lược.
3. **Trượt giá chưa tính.** Phí 10 bps là phí sàn, chưa gồm trượt giá; với
   lệnh nhỏ ở top 11 symbol thì không đáng kể, với lệnh lớn thì có.
4. **Thiên lệch sống sót.** 11 symbol là những đồng còn sống hôm nay. Thiên
   lệch này làm **hại** vế short (đồng sống sót thì đã tăng), nên nó không giải
   thích được kết quả dương.
5. **Hiệu ứng đang mòn.** 2024 `+64,71` xuống 2026 `+13,94` bps. Có thể là chu
   kỳ, có thể là thị trường đã học. 2026 mới có 259 lệnh nên chưa kết luận được.

## Tệp

- `scripts/fetch_metrics_archive.py` — tải kho metrics (có vòng thử lại)
- `scripts/forced_flow_data.py` — ghép metrics với giá, cache `{symbol}-flow.npz`
- `scripts/forced_flow.py` — bảng 5×5, đối chứng, null max-over-N, mổ xẻ
- `scripts/forced_flow_focus.py` — null riêng từng thống kê + theo năm
- `scripts/forced_flow_causal.py` — bản nhân quả hoàn toàn (phân vị trượt)
- `reports/forced_flow_local.json` — số liệu thô

---

# Phần 2 — ghép hình học với vị thế

Câu hỏi: đường cơ sở hình học (mother bar, span, cụm chạm) và tín hiệu vị thế
là hai thứ độc lập theo cấu tạo. Ghép lại có ra gì không?

## Tại sao phép thử này sắc

Tại thời điểm **khớp**, mọi lệnh đều cách cắt lỗ 1 span và chốt lời k span. Xác
suất hình học chạm chốt trước = `1/(1+k)` cho **tất cả** lệnh, và đã đo được là
hiệu chuẩn gần như hoàn hảo (lệch −0,0%, KTC ±2,1%, 47.533 mẫu). Nghĩa là
ngưỡng so sánh không phải một ước lượng mà là **một hằng số biết trước**. Bất
kỳ biến nào phân tách được kết quả ở đây đều mang thông tin ngoài hình học.

## Chiều 1 — vị thế làm bộ lọc cho lệnh hình học

Chia lệnh làm hai nhóm theo quan hệ giữa chiều phá và đám đông, dùng đúng đường
ống nhân quả của Phần 1, đọc tại lúc **nến chạm đóng cửa**:

| Khung | TP | OI cao | n thuận | n ngược | Thắng thuận | Thắng ngược | ΔW | KTC95 ΔW | **E thuận** | E ngược |
|---|---|---|---|---|---|---|---|---|---|---|
| 1h | 1 | — | 9.705 | 7.332 | 50,6% | 49,4% | +1,1% | [−1,1 ; +3,4] | −0,008 R | −0,061 |
| 1h | 2 | — | 9.705 | 7.332 | 32,3% | 29,6% | +2,8% | [+0,5 ; +5,0] | **+0,018 R** | −0,104 |
| 1h | 2 | có | 2.526 | 1.925 | 33,1% | 31,7% | +1,4% | [−2,8 ; +5,5] | +0,041 R | −0,027 |
| 4h | 1 | — | 2.632 | 1.480 | 49,5% | 45,6% | +3,9% | [−0,8 ; +8,8] | −0,009 R | −0,084 |
| 4h | 2 | — | 2.632 | 1.480 | 30,9% | 28,5% | +2,4% | [−2,2 ; +7,1] | −0,001 R | −0,077 |
| 4h | 2 | có | 656 | 321 | 28,0% | 35,5% | −7,5% | [−17,0 ; +1,6] | −0,111 R | +0,071 |

Null max-over-8 (xáo nhãn nhóm theo cụm, 2.000 lần): p95 `8,9%`, |ΔW| lớn nhất
thật `7,5%` → **p = 0,113**. Không vượt.

Bốn ô **không** cổng OI đều cùng dấu dương (+1,1 … +3,9 điểm) — nhất quán,
nhưng nhỏ. Bốn ô **có** cổng OI đổi dấu lung tung. Và quan trọng nhất: ngay cả
nhóm thuận lợi nhất cũng chỉ đạt **32,3% thắng so với điểm hòa vốn 33,3%**.
Kỳ vọng ròng `+0,018 R` — về thực chất là số không.

## Chiều 2 — hình học làm bộ lọc thời điểm cho lệnh vị thế

Giữ nguyên lệnh vị thế 1 ngày, nhưng chỉ vào ở **nến chạm** thay vì ở nhịp bất kỳ:

| Cách vào | Thuận ép | Ngược ép | Chênh | n |
|---|---|---|---|---|
| Có hình học (vào ở nến chạm) | +11,66 bps | −17,21 bps | +28,87 | 10.244 |
| Không hình học (mọi nhịp, cùng điều kiện đám đông) | +19,13 bps | −19,13 bps | **+38,25** | 6.870 |

Hình học làm lệnh vị thế **kém đi**, không tốt lên.

## Tại sao không ghép được — số học

| | Khung 1h | Khung 4h |
|---|---|---|
| 1 R (= 1 span) bằng bao nhiêu bps giá | **212 bps** | **445 bps** |
| Thời gian giữ lệnh, trung vị | 10,8 giờ | 44,2 giờ |
| Độ trôi vị thế trong cả kỳ giữ lệnh | ~40 bps | ~70 bps |
| Độ trôi tính theo span | **0,19 span** | **0,16 span** |

Đó là toàn bộ câu chuyện. Lợi thế vị thế là một **độ trôi có hướng, nhỏ**. Lệnh
hình học là một **cuộc đua giữa hai rào lớn**. Một độ trôi bằng 1/5 span không
đủ sức đẩy một cuộc đua rào ±1 span — kết quả vẫn do nhiễu chạm rào quyết định.
Chênh lệch quan sát được `+0,12 R` đúng cỡ mà số học dự đoán (~2 × 0,19 span,
bị rào cắt bớt còn khoảng một phần ba), nên đây không phải nhiễu — nó chỉ **quá
nhỏ so với thước đo**.

Muốn thu độ trôi 40 bps thì phải giữ lệnh tới một **điểm dừng theo thời gian**,
không phải thả vào một cuộc đua rào ±212 bps. Và khi đã làm vậy thì không cần
hình học nữa: bảng ở Chiều 2 cho thấy vào ở nhịp bất kỳ còn tốt hơn.

## Tệp

- `scripts/touch_flow_combo.py` — ghép hai hướng, null max-over-8

---

# Phần 3 — hạn chế thua lỗ

Điểm xuất phát: giữ 24 giờ, không cắt lỗ không chốt lời. Sharpe 0,89 · sụt giảm
23,3% · lệnh lỗ nhất **−2.961 bps**.

**Mọi con số dưới đây đo ở cùng một mức biến động 20%/năm.** So hai cách ở hai
mức đòn bẩy khác nhau là so nhầm — cách nào đặt cỡ lớn hơn sẽ luôn có CAGR cao
hơn *và* sụt giảm sâu hơn. Chuẩn hoá rồi thì CAGR và sụt giảm mới so được.

Đường giá giải quyết trên nến **5 phút** thật; chạm cả hai rào trong cùng một
nến tính **thua**; lệnh dừng khớp ở mức hoặc tệ hơn.

## A · Cắt lỗ — chỉ loại rất chặt mới có ích

| Cắt lỗ | bps/lệnh | Thắng | Lệnh lỗ nhất | Sharpe | Sụt giảm |
|---|---|---|---|---|---|
| không | 29,3 | 47,3% | −2.961 | **0,89** | 23,3% |
| 0,25 σ | 11,9 | 22,0% | −410 | 0,57 | 20,6% |
| 0,375 σ | 14,9 | 30,6% | −617 | 0,65 | 17,0% |
| **0,5 σ** | 21,7 | 36,3% | **−827** | **0,83** | **19,6%** |
| 0,625 σ | 18,3 | 39,8% | −1.043 | 0,67 | 19,7% |
| 0,75 σ | 17,0 | 42,3% | −1.184 | 0,61 | 23,0% |
| 1,0 σ | 16,3 | 44,8% | −1.559 | **0,55** | **27,1%** |
| 2,0 σ | 21,5 | 47,1% | −2.397 | 0,68 | 27,7% |
| 3,0 σ | 23,0 | 47,2% | −3.845 | 0,69 | 28,9% |

Cắt lỗ **1 σ là tệ nhất trên cả hai trục** — vừa mất lợi nhuận vừa sụt giảm sâu
hơn không cắt gì. Đó là bẫy "cho lệnh có chỗ thở": đủ rộng để bị nhiễu chạm,
không đủ rộng để tránh nó.

Một sự thật cơ học phải nói rõ: trong 54% số lệnh bị cắt ở 0,5 σ, **nếu không
cắt thì kết cục trung bình là −215 bps, còn cắt cho −230 bps**. Lệnh cắt lỗ
*không* làm những lệnh đó tốt lên. Toàn bộ lợi ích đến từ việc **chặt đuôi
phương sai**, nhờ đó ở cùng mức rủi ro được phép đặt cỡ lớn hơn.

## B · Chốt lời — không bao giờ

| Chốt lời | bps/lệnh | Thắng | Sharpe |
|---|---|---|---|
| không | 29,3 | 47,3% | **+0,89** |
| 3,0 σ | 9,2 | 47,3% | +0,33 |
| 2,0 σ | −3,3 | 47,4% | −0,12 |
| 1,0 σ | −28,7 | 50,9% | −1,31 |
| 0,5 σ | −41,4 | **62,3%** | **−2,25** |

Chốt lời 0,5 σ nâng tỉ lệ thắng lên 62,3% và biến chiến lược thành **âm nặng**.
Đây là bằng chứng mạnh nhất rằng lợi thế *chính là* đuôi phải: cắt đuôi phải đi
là không còn gì.

## C · Cỡ lệnh tỉ lệ nghịch với biến động

| | Sharpe | CAGR | Sụt giảm |
|---|---|---|---|
| cỡ cố định | 0,89 | 17,3% | 23,3% |
| cỡ theo biến động | **1,00** | 19,8% | 25,1% |

Đây là cải thiện **bền vững nhất**, vì nó không có tham số nào chỉnh được hình
dạng — mọi mức mục tiêu (1%/1,5%/2%/3%) cho Sharpe y hệt nhau sau khi chuẩn
hoá; mức mục tiêu chỉ chọn đòn bẩy.

## D, E · Hai cách KHÔNG hiệu quả

**Thắt chặt ngưỡng vào lệnh** (0,15 / 0,10 / 0,05 thay vì 0,20): Sharpe 0,62 /
0,84 / 0,41 — không có gì hơn 0,89.

**Chặn số lệnh mở đồng thời**: ở cùng mức biến động, chặn 1 lệnh cho sụt giảm
30,8%, chặn 3 cho 23,1%, không chặn 23,3%. Không khác gì.

> Ghi lại một lần đọc sai của chính tôi: lần chạy đầu bảng E cho "chặn 1 lệnh →
> sụt giảm 8,2%", nghe như phát hiện lớn. Nó là ảo: tôi đã đặt cỡ nhỏ hơn cho
> biến thể đó. Chuẩn hoá biến động xong thì con số thành 30,8%.

## Kết hợp tốt nhất — và lý do chưa nên tin hẳn

| | bps/lệnh | Lệnh lỗ nhất | Sharpe | CAGR | Sụt giảm |
|---|---|---|---|---|---|
| gốc | 29,3 | −2.961 | 0,89 | 17,3% | 23,3% |
| + cỡ theo biến động | 29,3 | −2.961 | 1,00 | 19,8% | 25,1% |
| **+ cắt lỗ 0,5 σ** | 21,7 | **−827** | **1,06** | **21,3%** | **16,7%** |

Tốt hơn trên **mọi trục**: lệnh lỗ nhất giảm 3,6 lần, sụt giảm giảm 28%, Sharpe
và CAGR đều tăng. Và nó ổn định qua thời gian theo cách bản gốc không có:

| Sharpe theo năm | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| gốc | +0,69 | +0,82 | **+2,21** | +0,64 | **+0,13** |
| gốc + cỡ | +0,91 | +1,10 | +2,70 | +0,47 | **+0,05** |
| 0,5 σ + cỡ | +0,72 | +1,19 | +1,46 | +0,56 | **+1,64** |

Cắt lỗ chặt **nhường lại phần thắng lớn của 2024** nhưng **cứu được 2026** — cái
năm mà bản gốc gần như chết. Hai nửa thời gian: 1,15 / 0,96 (bản gốc 1,04 /
0,73).

**Nhưng 0,5 σ là một đỉnh nhọn, không phải cao nguyên.** Hai mức kề bên cho
Sharpe 0,93 và 0,92, còn xét theo nửa thời gian thì chúng không ổn định
(0,375 σ: 0,57/0,77 · 0,625 σ: 0,74/0,60). Một tham số mà lệch 25% là mất hết
lợi ích thì chưa đủ tin để chạy thật — cần kiểm walk-forward trước.

## Tệp

- `scripts/forced_flow_risk.py` — quét A–F, chuẩn hoá biến động

---

# Phần 4 — giữ lệnh lời lâu hơn

Giữ nguyên dừng-theo-thời-gian, không cắt lỗ. Chỉ đổi cách thoát: cho lệnh
**đang lời** chạy tiếp. Đối chứng bắt buộc chạy trước: giữ **mọi** lệnh lâu hơn.

Lãi/lỗ **đánh dấu theo ngày** (mark to market) chứ không dồn hết vào ngày đóng
lệnh — dồn cục thì biến thể giữ lâu có biến động giả tạo. Phí 10 bps tính **một
lần**, nên giữ lâu không tốn thêm phí: đó là điểm có lợi sẵn cho các cách gia hạn.

## A · Đối chứng: giữ mọi lệnh lâu hơn

| Giữ | bps/lệnh | Thắng | Sharpe | Sụt giảm |
|---|---|---|---|---|
| 1 ngày | 25,0 | 47,3% | 0,79 | 24,2% |
| **2 ngày** | **55,5** | 50,8% | **1,01** | **20,0%** |
| 3 ngày | 54,7 | 51,3% | 0,75 | 22,1% |
| 5 ngày | 54,9 | 50,6% | 0,53 | 27,1% |
| 7 ngày | 59,0 | 49,4% | 0,44 | 27,5% |
| 10 ngày | 79,1 | 51,0% | 0,45 | 23,4% |

Lợi nhuận **chững lại từ ngày 2** (~55 bps) trong khi phương sai tiếp tục lớn
lên, nên Sharpe giảm đều sau đó. Đó là hình dạng của một độ trôi cạn sau 2 ngày.

## B, C, D · Cho riêng lệnh lời chạy tiếp — đều KÉM HƠN

| Cách | bps/lệnh | Thắng | Sharpe |
|---|---|---|---|
| giữ đều 2 ngày (đối chứng) | **55,5** | 50,8% | **1,01** |
| lời → gia hạn tới 2 ngày | 37,8 | 37,3% | 0,79 |
| lời → gia hạn tới 5 ngày | 30,4 | 32,1% | 0,40 |
| gia hạn cuốn, tối đa 5 ngày | 37,2 | 25,1% | 0,52 |
| gia hạn cuốn, tối đa 10 ngày | 58,2 | 18,6% | 0,65 |
| cắt lỗ trượt 0,5 σ sau 24h | 21,6 | 44,6% | 0,66 |
| cắt lỗ trượt 2 σ sau 24h | −1,0 | 28,8% | −0,02 |

**Chọn lệnh thắng để gia hạn luôn tệ hơn gia hạn tất cả.** Lý do đơn giản: nếu
độ trôi còn chạy sang ngày 2 thì nó chạy cho **cả lệnh đang lỗ**. Đóng lệnh lỗ
ở giờ thứ 24 là vứt đúng phần hồi của chúng đi. Nâng ngưỡng "đang lời" lên
1 σ chỉ đưa Sharpe về 0,89 — bằng lúc chưa làm gì.

## Nhưng đối chứng giờ vào lệnh làm hỏng kết luận A

Lưới ngày có bước cố định, nên **mọi lệnh của một symbol đều vào ở cùng một giờ
trong ngày**, và thoát 24 giờ sau cũng rơi đúng giờ đó. Dịch lưới rồi đo lại:

| Thoát | dịch 0 | dịch 72 | dịch 144 | dịch 216 | TB | độ lệch |
|---|---|---|---|---|---|---|
| 24 giờ | 25 | 22 | 19 | 34 | **25** | **6** |
| 48 giờ | 55 | 44 | 23 | 53 | 44 | 13 |
| 72 giờ | 55 | 51 | 33 | 50 | 47 | 8 |
| nửa 24h + nửa 48h | 40 | 33 | 21 | 44 | 34 | 9 |

Con số **24 giờ ổn định nhất**. Cú nhảy "1,5 ngày" trong lưới đầu tiên phần lớn
là hiệu ứng **giờ trong ngày**, không phải độ trôi.

Đo thẳng độ trôi **riêng từng ngày** (KTC theo block 7 ngày lịch):

| Ngày | dịch 0 | dịch 144 |
|---|---|---|
| 1 | **+35,0** `[+9,8 ; +61,5]` | **+28,6** `[+3,6 ; +54,4]` |
| 2 | **+30,5** `[+5,6 ; +55,3]` | +4,5 `[−20,5 ; +29,6]` |
| 3 | −0,8 `[−28,1 ; +25,3]` | +10,1 `[−15,9 ; +37,2]` |
| 4 | −4,1 | −6,6 |
| 5 | +4,3 | +5,8 |

**Ngày 1 chắc** — cả hai mốc dịch đều không chứa 0. **Ngày 2 bấp bênh** — mạnh
ở một giờ vào lệnh, biến mất ở giờ khác. **Ngày 3 trở đi: không có gì.**

## Kết luận

1. **Không cho riêng lệnh lời chạy tiếp.** Mọi biến thể đều kém hơn giữ đều,
   ở mọi chân trời. Cắt lỗ trượt sau 24 giờ còn tệ hơn nữa.
2. **Giữ 2 ngày cho tất cả** nâng lợi nhuận mỗi lệnh từ ~25 lên ~44 bps tính
   trung bình trên bốn giờ vào lệnh, nhưng độ lệch giữa các giờ là 13 bps —
   gấp đôi độ lệch của con số 24 giờ. Chưa đủ chắc để đổi.
3. **Giới hạn thiết kế mới phát hiện:** lưới ngày khiến mọi lệnh vào cùng một
   giờ. Con số 24 giờ sống sót qua phép dịch (19–34 bps), nhưng mọi kết luận
   về chân trời dài hơn đều phải đo lại trên nhiều mốc dịch.

## Tệp

- `scripts/forced_flow_hold.py` — bảng A–E, `build(off=…)` để dịch lưới ngày

---

# Phần 5 — còn đặc trưng nào nâng được độ chính xác?

Giữ nguyên luật: cổng OI ≥ 0,8 · đám đông ngoài 0,2/0,8 · vào trễ 1 nhịp · giữ
24 giờ · không cắt lỗ không chốt lời. Chỉ hỏi: **trong tập lệnh này**, có biến
nào tách được lệnh thắng khỏi lệnh thua?

Đo bằng tương quan hạng Spearman giữa đặc trưng và lãi/lỗ **ròng**, kèm bảng ba
phân vị. Nhiễu: xáo lãi/lỗ theo **block 7 ngày lịch**, max trên cả 13 đặc trưng.
Và theo bài học Phần 4, mỗi đặc trưng **đo lại trên 4 mốc dịch lưới ngày**.

| Đặc trưng | rho | p | ba phân vị (bps) | cao−thấp | 4 mốc |
|---|---|---|---|---|---|
| d_oi_1d | −0,016 | 0,509 | +2 / +64 / +22 | +20 | cùng dấu |
| **d_oi_4h** | **+0,056** | 0,015 | +23 / +14 / **+51** | **+28** | **cùng dấu** |
| d_crowd | −0,016 | 0,505 | +55 / +11 / +22 | −32 | lệch |
| div_top | +0,005 | 0,845 | +41 / +11 / +20 | −22 | lệch |
| taker | −0,036 | 0,138 | +44 / +65 / −8 | −51 | lệch |
| ret_1d | −0,055 | 0,019 | +30 / +22 / +35 | +5 | cùng dấu |
| ret_7d | −0,053 | 0,019 | +28 / +22 / +38 | +10 | cùng dấu |
| vol | −0,004 | 0,858 | −2 / +41 / +49 | +52 | lệch |
| fund | +0,017 | 0,453 | **+29 / +30 / +29** | **+0** | cùng dấu |
| fund_3d | +0,012 | 0,595 | +21 / +34 / +33 | +11 | lệch |
| d_fund | +0,030 | 0,183 | +24 / −5 / +69 | +45 | lệch |
| breadth | +0,033 | 0,163 | +18 / +26 / +38 | +20 | cùng dấu |
| **same_side** | **+0,052** | 0,023 | +17 / +19 / **+47** | **+29** | **cùng dấu** |

Null max-over-13: p95 |rho| = **0,067**. Lớn nhất thật = 0,056 (`d_oi_4h`),
**p = 0,203**. **Không đặc trưng nào vượt.**

## Hai ứng viên đáng theo dõi (chưa chứng minh được)

- **`d_oi_4h`** — OI *đang được chất thêm* trong 4 giờ qua. Ba phân vị
  +23/+14/+51, cùng dấu ở cả 4 mốc dịch. Chuyện kể hợp lý: vị thế mới = nhiên
  liệu mới.
- **`same_side`** — đám đông lệch một bên **trên cả thị trường**, không riêng
  symbol này. Ba phân vị +17/+19/+47, đơn điệu, cùng dấu ở cả 4 mốc. Đo theo
  độ rộng: <20% symbol khác cùng phía → +17,7 bps · 20–40% → +25,7 · >40% →
  **+37,6**. Chuyện kể: đám đông lệch toàn thị trường thì dễ đổ dây chuyền hơn.

## Kết quả âm đáng chú ý nhất: funding

`fund` cho ba phân vị **+29 / +30 / +29 bps** — bằng phẳng tuyệt đối. **Chi phí
mà bên đông người đang trả không thêm một chút thông tin nào** ngoài việc họ
đông. Đây là kết quả âm có ý nghĩa, không phải kết quả rỗng: nó nói hiệu ứng
này **không phải** chuyện áp lực carry.

Cùng loại âm: lệch giữa bán lẻ và top trader (`div_top`), chế độ biến động
(`vol`), mất cân bằng taker (`taker`) — cả ba đều đổi dấu giữa các mốc dịch.

## Giới hạn quyết định mọi thứ ở trên

Với **1.802 lệnh** và nhiễu theo block 7 ngày, dữ liệu này **chỉ thấy được đặc
trưng tạo ra chênh lệch ba phân vị từ ~67 bps trở lên** (khoảng 55–93). Hai ứng
viên trên nằm ở mức ~28–29 bps — đúng vùng mà "có thật nhưng quá nhỏ để chứng
minh" và "nhiễu" **không phân biệt được**.

Nên câu trả lời thật cho "làm sao nâng độ chính xác" **không phải thêm đặc
trưng**. Là **thêm symbol**. Kho `metrics` phủ hàng trăm hợp đồng; đi từ 11 lên
50 symbol đưa số lệnh từ ~1.800 lên ~8.000, hạ ngưỡng phát hiện xuống còn
khoảng một nửa, và mới đủ sức phân giải hai ứng viên trên. Chi phí: ~25 MB và
~200 giây mỗi symbol.

## Tệp

- `scripts/forced_flow_feats.py` — 13 đặc trưng, 4 mốc dịch, null max-over-13,
  kèm ước lượng ngưỡng phát hiện

---

# Phần 6 — mở rộng vũ trụ symbol (đang chạy, ảnh chụp 16/51)

Phần 5 kết luận nút thắt là **số lệnh**, không phải thiếu đặc trưng. Đang tải
thêm 40 symbol (chọn theo khối lượng 24h, niêm yết ≥ 500 ngày). Dưới đây là
ảnh chụp khi có **16 symbol**: 11 gốc + BCH, LTC, FIL, FET, ENA.

## Ngoài mẫu — phép thử thật sự đầu tiên

5 symbol mới chưa từng tham gia bất kỳ quyết định thiết kế nào (ngưỡng 0,2/0,8,
cổng OI, cửa sổ 30/90 ngày, chân trời 24 giờ đều chốt trước khi chúng có mặt).

| Tập | gộp bps/lệnh | Cắt đuôi 1% | Thắng | n lệnh | Độ phủ |
|---|---|---|---|---|---|
| 11 gốc (trong mẫu) | +39,0 | +25,9 | 49,1% | 1.802 | 8/11 |
| **5 mới (ngoài mẫu)** | **+28,1** | +24,6 | 49,6% | 788 | 4/5 |
| cả 16 | +35,7 | +25,5 | 49,2% | 2.590 | 12/16 |

Từng cái: FET **+105,0** · BCH **+76,6** · FIL +25,2 · ENA +11,8 · **LTC −58,7**.

**Hiệu ứng sống sót ngoài mẫu**, nhưng yếu hơn trong mẫu (+28 so với +39) —
đúng như phải kỳ vọng. LTC là symbol âm mạnh nhất cả bộ.

## Gộp 16 symbol

| | 11 symbol | 15 symbol | **16 symbol** |
|---|---|---|---|
| gộp bps/lệnh | +39,0 | +43,5 | **+35,7** |
| Cắt đuôi 1% | +25,9 | +32,2 | +25,5 |
| Null p95 \|.\| | 48,4 | 39,7 | **38,5** · thật **+70,8** · p < 0,002 |
| CI 95% | [+23,2 ; +133,6] | [+41,7 ; +132,4] | **[+28,5 ; +116,1]** |

Theo năm: 2022 +22,9 · 2023 +34,7 · 2024 +54,0 · 2025 +21,9 · **2026 +30,6**.

**Tôi đã nhấn sai một điểm ở Phần 1.** "Hiệu ứng đang mòn, 2026 chỉ +14 bps"
phần lớn là nhiễu mẫu nhỏ: với 371 lệnh thay vì 259, 2026 về +30,6 — ngang mức
trung bình lịch sử. Không có bằng chứng về suy thoái.

## Ghi lại ba lỗi của lần tải đầu

1. **Song song 3 luồng làm CHẬM đi 25 lần.** 18 kết nối đồng thời tới
   `data.binance.vision` bị bóp; FILUSDT mất 18.638 s so với ~200 s khi chạy
   tuần tự. Đã quay về một luồng.
2. **Cắt số ngày theo `onboardDate` làm hỏng tên file cache.** `price_only`
   đặt tên theo số ngày *yêu cầu*, còn `_price()` tìm đúng chuỗi `2100d`.
3. **Và lỗi đó giết tiến trình:** `_price()` báo lỗi bằng `SystemExit`, không
   phải `Exception`, nên `try/except Exception` của vòng lặp không bắt được.
   Hai trong ba tiến trình chết im lặng ở symbol đầu tiên.

`_price()` nay lấy bản npz **dài nhất** bằng glob và báo `FileNotFoundError`.

---

# Phần 7 — trả nợ: chạy đối chứng giờ vào lệnh cho MỌI cải tiến

Cuối Phần 4 tôi ghi: *"Phần 3 tôi chưa chạy đối chứng này — nên đặt dấu hỏi lên
nó cho tới khi chạy."* Đây là lúc chạy. Mọi cấu hình đã đề xuất, đo lại trên cả
**4 mốc dịch lưới ngày**, vũ trụ 17 symbol, CAGR và sụt giảm chuẩn hoá về cùng
mức biến động 20%/năm.

| Cấu hình | dịch 0 | dịch 72 | dịch 144 | dịch 216 | **Sharpe TB** |
|---|---|---|---|---|---|
| **gốc** | 1,10 | 0,88 | 0,89 | 1,20 | **1,02** |
| + cỡ theo biến động | 1,14 | 1,04 | 0,82 | 1,15 | **1,03** |
| + cắt lỗ 0,5 σ | 0,97 | **0,21** | **0,39** | 0,58 | **0,54** |
| + bỏ 1/3 `ret_1d` cao | 1,16 | 0,63 | 0,78 | 1,05 | 0,90 |
| cỡ + `ret_1d` | 1,10 | 0,69 | 0,66 | 0,91 | 0,84 |
| cỡ + `ret_1d` + cắt lỗ | 1,17 | 0,50 | 0,54 | 0,59 | 0,70 |

## Rút lại kết luận của Phần 3

**Cắt lỗ 0,5 σ là hiện vật của MỘT giờ vào lệnh.** Ở mốc dịch 0 nó cho Sharpe
0,97 đúng như Phần 3 đo được; ở ba mốc còn lại là 0,21 / 0,39 / 0,58. Trung
bình 0,54 so với 1,02 của bản gốc — **nó làm hỏng chiến lược, không cải thiện**.

Phần 3 đã cảnh báo "0,5 σ là một đỉnh nhọn, không phải cao nguyên" và khuyên
kiểm walk-forward trước khi dùng. Đối chứng giờ vào lệnh rẻ hơn walk-forward và
đã đủ để bác bỏ. **Đừng dùng cắt lỗ.**

## `ret_1d` cũng không qua được

Tương quan hạng của `ret_1d` với lãi/lỗ là thật và ổn định về dấu trên cả 4 mốc
(rho −0,069, p = 0,005, vượt null max-over-13). **Nhưng dấu ổn định không có
nghĩa là bộ lọc ổn định.** Luật "bỏ 1/3 cao nhất" cho Sharpe 1,16 ở mốc 0 và
0,63 ở mốc 72; trung bình 0,90, thấp hơn bản gốc.

Lý do: bỏ một phần ba số lệnh làm rủi ro cô đặc lại, và phần lợi thế mỏng của
`ret_1d` không bù nổi. Một đặc trưng có thể **có thật mà vẫn không dùng được**.

## Chỉ một thứ sống sót, và nó gần như không đổi gì

Cỡ lệnh theo biến động: 1,02 → 1,03. Trong phạm vi nhiễu. Nó không có tham số
nào chỉnh được hình dạng nên vẫn là lựa chọn an toàn, nhưng đừng kỳ vọng nó
thêm được gì.

## Kết luận của cả sáu phần cải tiến

**Bản gốc — không cắt lỗ, không chốt lời, không lọc đặc trưng, giữ đúng 24 giờ
— là cấu hình tốt nhất tìm được.** Sharpe trung bình 1,02 qua bốn giờ vào lệnh
(biên 0,88–1,20).

Sáu hướng đã thử và kết cục:

| Hướng | Kết cục |
|---|---|
| Ghép với hình học (Phần 2) | Độ trôi bằng 1/5 span, quá nhỏ cho rào |
| Cắt lỗ (Phần 3 → 7) | **Rút lại** — hiện vật của một giờ vào lệnh |
| Chốt lời (Phần 3) | Phá hỏng hoàn toàn, lợi thế nằm ở đuôi phải |
| Giữ lệnh lời lâu hơn (Phần 4) | Kém hơn giữ đều mọi lệnh |
| Thêm đặc trưng (Phần 5 → 6) | `ret_1d` có thật nhưng không dùng được |
| Cỡ theo biến động (Phần 3) | Sống sót, gần như không đổi gì |

---

# Phần 8 — chốt trên toàn bộ 51 symbol

Tải xong 37/37 symbol mới. Vũ trụ cuối: **51 symbol**, ~6.900 lệnh mỗi mốc dịch.

## Hiệu ứng có thật về mặt thống kê

| | |
|---|---|
| S (mốc dịch 0) | **+51,15 bps** |
| Null 500 lần dịch vòng tròn | TB +0,9 · p95 \|.\| **26,5** |
| **p hai phía** | **< 0,002** |
| CI 95% block 7 ngày | [+21,9 ; +82,2] |
| Độ phủ | 30/39 symbol |

Không có nghi ngờ gì về việc có một mối quan hệ. Nó sống qua null dịch vòng
tròn, qua bootstrap block, qua bốn mốc dịch lưới, và qua 40 symbol chưa từng
tham gia thiết kế.

## Nhưng về mặt kinh tế thì không

| Mốc dịch | bps ròng/lệnh | Sharpe | Sụt giảm |
|---|---|---|---|
| 0 | +17,2 | 0,83 | 24% |
| 72 | +15,6 | 0,74 | 32% |
| 144 | +16,6 | 0,77 | 23% |
| 216 | **+11,1** | **0,51** | **41%** |
| **TB** | **+15,1** | **0,71** | **30%** |

Phí 10 bps ⇒ biên còn **5 bps mỗi lệnh**.

| Năm | % tổng lợi | bps/lệnh |
|---|---|---|
| 2022 | 14,5% | +18,4 |
| 2023 | 17,9% | +15,8 |
| **2024** | **47,4%** | **+29,0** |
| **2025** | **−0,5%** | **−0,3** |
| 2026 | 17,5% | +14,4 |

**Bỏ 2024 ra: +10,6 bps/lệnh — đúng bằng phí.** Ô (symbol × năm) dương:
**51%**, tức tung đồng xu.

## Con số quyết định

| Tập | bps ròng/lệnh | Symbol dương |
|---|---|---|
| **11 symbol GỐC** (đã đi qua mọi quyết định thiết kế) | **+25,9** | 9/11 |
| **40 symbol MỚI** (chưa từng tham gia) | **+8,7** | 25/40 |

Trên vũ trụ không tham gia thiết kế, **lợi thế gộp 8,7 bps nằm DƯỚI sàn phí
10 bps** — và 10 bps là giả định của đồng lớn; các đồng nhỏ trong nhóm mới có
chênh lệch mua-bán và trượt giá cao hơn.

Tốt nhất / tệ nhất: INJ +91, LSK +85, XRP +68 … POL −139, UNI −93, ONDO −91.
Âm ở cả 4 mốc dịch: POL, UNI, ONDO, RARE, APT, LTC, OP, NMR, GRT, NEAR, BNB.

## Kết luận

**Có hiệu ứng thật, đo được, p < 0,002 — và không giao dịch được.**

Vị thế đám đông (`count_long_short_ratio`) có chứa thông tin về giá 24 giờ kế
tiếp, theo chiều ngược đám đông. Điều đó đã được chứng minh ở mức chặt chẽ
nhất mà phiên này làm được. Nhưng biên độ của nó, trên một vũ trụ không bị
chọn lọc, không đủ bù chi phí giao dịch — và gần một nửa toàn bộ lợi nhuận
lịch sử đến từ riêng năm 2024.

Con số +39 bps của 11 symbol ban đầu không sai; nó chỉ là con số của một tập
thuận lợi. Đường đi từ +39 (11 symbol) → +29 (17) → +19 (27) → +17 (40) →
+15 (51) là đơn điệu, và đó là hình dạng của chọn lọc chứ không phải của một
hiệu ứng bền.

---

# Phần 9 — khối lượng và giá trước đó

Phần 5 chỉ thử `taker` (một **tỉ lệ** mua/bán) và `vol` (biến động, tức giá).
**Mức khối lượng chưa từng được thử.** Thêm sáu biến, thành 19:

```
v_1h    khối lượng 1 giờ qua ÷ khối lượng giờ trung bình 30 ngày
v_1d    khối lượng 24 giờ qua ÷ mức trung bình 30 ngày
turn    khối lượng 24h × giá ÷ giá trị OI
casc    −sign(ΔOI 4h) × log(v_1h) — khối lượng vọt lên TRONG KHI OI tụt
ret_4h  giá 4 giờ trước, ký theo chiều lệnh
rng     vị trí giá trong biên độ 30 ngày, ký theo chiều lệnh
```

Chạy trên **51 symbol, 6.865 lệnh** — gấp 3,8 lần Phần 5, nên ngưỡng null hạ
từ 0,067 xuống **0,037**.

## Bảng tương quan

| Đặc trưng | rho | p | Ba phân vị (bps) | 4 mốc |
|---|---|---|---|---|
| ret_7d | −0,067 | 0,000 | +9 / +22 / +20 | cùng dấu |
| **same_side** | **+0,058** | **0,000** | **−2 / +23 / +29** | **cùng dấu** |
| rng | −0,055 | 0,000 | +15 / +9 / +27 | cùng dấu |
| ret_1d | −0,053 | 0,000 | +26 / +8 / +17 | cùng dấu |
| **breadth** | **+0,050** | **0,000** | −12 / +42 / +19 | **cùng dấu** |
| ret_4h | −0,048 | 0,000 | +27 / +24 / +0 | lệch |
| turn | −0,033 | 0,006 | +16 / −0 / +36 | cùng dấu |
| v_1d | −0,026 | 0,030 | +20 / −7 / +38 | cùng dấu |
| v_1h | −0,025 | 0,040 | +20 / +11 / +20 | lệch |
| **casc** | +0,020 | **0,100** | +10 / +12 / +30 | cùng dấu |

**Cảnh báo phải đọc trước:** nhiều biến có `rho` và chênh lệch ba phân vị
**ngược dấu nhau** (ret_7d, rng, turn, v_1d). Khi hai thước đo cùng một quan hệ
nói ngược nhau thì quan hệ đó không đơn điệu, và `rho` một mình không đủ.

## Khối lượng: gần như không thêm gì

`v_1h` lệch dấu giữa các mốc dịch. `v_1d` và `turn` có mâu thuẫn rho/phân vị.
Và **`casc` — chữ ký thanh lý dây chuyền mà tôi trông đợi nhất — cho p = 0,100,
không vượt ngưỡng.** Ba phân vị của nó (+10/+12/+30) đơn điệu và đúng chiều dự
đoán, nhưng không đủ mạnh.

Kết quả âm này có ý nghĩa: **việc bị ép đóng lệnh, ở mức có thể đo bằng khối
lượng 5 phút, không mang thêm thông tin ngoài việc đám đông đang đứng đâu.**

## Nhưng tương quan có ý nghĩa ≠ bộ lọc dùng được

Bài học Phần 7. Thử từng biến làm bộ lọc (giữ 2/3 về phía tốt), đo trên cả
4 mốc dịch:

| Cấu hình | bps TB | Sharpe TB | Sharpe 4 mốc |
|---|---|---|---|
| gốc, không lọc | 15,1 | 0,71 | 0,83 0,74 0,77 0,51 |
| **breadth: giữ 2/3 cao** | **25,5** | **0,93** | 1,13 0,90 1,15 0,54 |
| rng: giữ 2/3 cao | 23,1 | 0,86 | 0,70 0,91 1,04 0,81 |
| ret_7d: giữ 2/3 cao | 21,2 | 0,77 | 0,79 0,80 0,97 0,52 |
| same_side: giữ 2/3 cao | 19,1 | 0,69 | 0,95 0,84 0,76 0,21 |
| casc / turn / v_1d | ≤ 18,6 | ≤ 0,65 | đều dưới gốc |

## Kiểm chứng ngoài mẫu — chỗ quyết định

| `breadth` | bps | Sharpe |
|---|---|---|
| 11 symbol GỐC, không lọc | 26,0 | 0,87 |
| 11 symbol GỐC, **có lọc** | 28,2 | **0,76** ↓ |
| **40 symbol MỚI, không lọc** | **10,7** | **0,47** |
| **40 symbol MỚI, có lọc** | **24,5** | **0,78** ↑ |
| nửa sau thời gian, không lọc | 6,8 | 0,35 |
| nửa sau thời gian, có lọc | 15,8 | 0,60 ↑ |

**Bộ lọc độ rộng giúp đúng chỗ quan trọng nhất: 40 symbol ngoài mẫu.** Chúng đi
từ +10,7 bps (ròng +0,7, tức vô dụng) lên **+24,5 bps (ròng +14,5)**. Và nó
giúp ở cả hai nửa thời gian. Nó *làm hại* 11 symbol gốc — điều này hợp lý, vì
nó không được chọn trên tập đó.

## Vì sao tôi vẫn chưa gọi đây là phát hiện

**`same_side` đo gần như cùng một thứ và THẤT BẠI.** Nó là bản liên tục của
`breadth` (trung bình phân vị của các symbol khác, thay vì tỉ lệ vượt ngưỡng).
Nửa sau thời gian: Sharpe 0,04. Hai thước đo gần trùng nhau cho hai kết luận
ngược nhau — đó chính là hình dạng của nhiễu.

Thêm nữa: tôi đã thử **19 đặc trưng × 2 chiều = 38 cấu hình** rồi chọn ra cái
tốt nhất. Null max-over-19 áp cho *tương quan*, không áp cho *việc chọn bộ lọc*.
Kiểm chứng ngoài mẫu ở trên là biện hộ duy nhất, và nó chưa phải một phép hiệu
chỉnh chính thức.

## Trả lời gọn

**Giá:** đã thử từ Phần 5. `ret_1d`, `ret_7d`, `rng`, `ret_4h` đều vượt ngưỡng
tương quan. Chỉ `rng` và `ret_7d` cải thiện được Sharpe, và chỉ ở mức khiêm tốn.

**Khối lượng:** đến Phần 9 mới thử mức thật. Kết quả gần như âm — kể cả
`casc`, phép ghép khối-lượng-vọt-với-OI-tụt.

**Thứ đáng chú ý nhất lại không phải cả hai:** `breadth` — đám đông lệch một
bên trên **cả thị trường**, không riêng symbol này.
