# Động lượng cắt ngang điều chỉnh biến động — đã chốt

**Ngày chốt:** 26/10/2026 · **Dữ liệu:** nến 1D (UTC) của Binance USDⓈ-M
futures, **toàn bộ mã USDT perp từng tồn tại** kể cả đã huỷ niêm yết
(623 mã qua được bộ lọc perp-crypto), 2020-09 → 2026-10-25. Funding thật từ
`/fapi/v1/fundingRate`. Phí 10 bps khứ hồi mỗi vị thế mỗi kỳ.

Đây là chiến lược **cắt ngang** đầu tiên của kho này: nó không hỏi "mã này có
tín hiệu không" mà xếp hạng mọi mã **với nhau** tại mỗi thời điểm. Nó bổ sung
chứ không thay thế [RSI(2)](rsi2-connors.md) — hai cơ chế ngược chiều nhau về
chân trời: RSI(2) ăn **đảo chiều 2 ngày**, cái này ăn **động lượng 30 ngày**.

---

## Bộ tham số

```
vũ trụ   : top 20 mã theo trung vị giá trị giao dịch USD 30 ngày,
           xếp hạng lại MỖI NGÀY, chỉ tính perp crypto
điểm     : lợi suất 30 ngày ÷ độ lệch chuẩn lợi suất log 30 ngày
danh mục : MUA 2 mã điểm cao nhất, BÁN 2 mã điểm thấp nhất, vốn đều
lọc      : chỉ MUA nếu close > MA30, chỉ BÁN nếu close < MA30
           ứng viên không qua lọc bị BỎ HẲN, không thay bằng mã kế tiếp
nhịp     : tái cân bằng 7 ngày — chốt điểm ở close ngày d,
           khớp ở open ngày d+1, thoát ở open ngày d+8
phí      : 10 bps khứ hồi mỗi vị thế mỗi kỳ + funding thực tế
           (chân mua trả funding, chân bán nhận)
huỷ niêm : mã bị huỷ giữa kỳ thoát ở GIÁ CUỐI CÙNG CÓ, không được loại bỏ
triển khai: chia 1/7 vốn cho mỗi ngày trong tuần, chạy 7 sổ song song
```

Mỗi mã cần **205 nến lịch sử** trước khi được chọn. "2 mã mỗi chân" là
`max(2, 10% số mã đủ điều kiện)`; với vũ trụ top 20 thì luôn ra 2.

**Vì sao chia cho độ lệch chuẩn:** động lượng thô bị các token biến động cực
mạnh chiếm sóng — chúng luôn đứng đầu bảng chỉ vì chúng ồn, không vì chúng có
xu hướng. Mẫu số loại đúng phần đó. Hệ quả đo được ở § "Thô so với chia biến
động".

**Triển khai thật là 7 sổ, không phải 1.** Chu kỳ 7 ngày khoá chặt mọi kỳ vào
cùng một thứ trong tuần; một sổ đơn lẻ cho kết quả dao động **9,1× đến 54,7×**
tuỳ thứ. Chia đều 1/7 vốn cho cả bảy thứ khử hết phần may rủi đó.

**26,79× trong 5,5 năm · sụt theo ngày 44,1% · 94% số ngày dưới đỉnh**
**+143,3 bps/kỳ trung bình 7 sổ (độ lệch 21,9) · 5/6 năm dương**
**Đợt âm khỏi đỉnh dài nhất 493 ngày (16,2 tháng)**

**Hai tầng bằng chứng — đừng trộn.** Phần kiểm định nặng ở § "Ba phép kiểm nó
đã vượt" chạy trên **bản không lọc** (21,49× · sụt 45,7% · +134,4 bps/kỳ ·
đợt âm 660 ngày). Bộ lọc MA30 là **lựa chọn vận hành chốt thêm lên trên**, với
mức bằng chứng riêng của nó — xem § "Bộ lọc MA30". Nó **chưa** vượt ngưỡng đa
phép thử, và tài liệu này không tuyên bố ngược lại.

## Bộ lọc MA30 — ĐÃ CHỐT 26/10/2026

Luật thêm: **chỉ MUA nếu close > MA30, chỉ BÁN nếu close < MA30**.

Giả thuyết ban đầu của tôi là bộ lọc gần như thừa — MA30 và lợi suất 30 ngày
dùng chung một cửa sổ, nên mã đứng đầu bảng `ret/vol` đáng lẽ đã nằm trên
MA30. **Sai**:

```
chân MUA bị loại  743/4.038  (18,4%)
chân BÁN bị loại  732/4.038  (18,1%)
```

Gần một phần năm ứng viên bị chặn. Trường hợp điển hình: một mã có lợi suất
30 ngày rất cao (điểm cao) nhưng giá đã rơi lại xuống dưới trung bình — động
lượng nằm ở quá khứ, không còn ở hiện tại.

Hai cách diễn đạt, đo cả hai:

| biến thể | vị thế/kỳ | bps/kỳ | Vốn gộp | Sụt | CAGR/sụt |
|---|---|---|---|---|---|
| **gốc — không lọc** | 4,00 | +134,4 | **21,49×** | 45,7% | **1,43** |
| A · bỏ lệnh | 3,27 | +143,3 | 26,79× | **44,1%** | **1,61** |
| B · lọc trước khi xếp hạng | 3,50 | +148,1 | **29,78×** | 46,4% | 1,60 |

```
A − gốc:  +8,9 bps/kỳ · KTC95 [−22,7 ; +46,0]
B − gốc: +13,7 bps/kỳ · KTC95 [−17,1 ; +50,3]      (ghép cặp 2.019 kỳ)
```

| Năm | gốc | sụt | A | sụt | B | sụt |
|---|---|---|---|---|---|---|
| 2021 | 3,11× | 27,7% | 3,24× | **22,7%** | 3,16× | 26,5% |
| 2022 | 0,75× | 41,0% | 0,78× | **34,8%** | 0,77× | 36,9% |
| 2023 | 1,64× | 32,2% | 1,65× | 34,8% | 1,67× | 35,3% |
| 2024 | 2,13× | 25,9% | 2,01× | 26,4% | 2,09× | 26,3% |
| 2025 | 1,57× | 25,1% | **1,78×** | **20,0%** | 1,77× | 22,6% |
| 2026 | 1,70× | 32,3% | 1,81× | 33,5% | **2,00×** | **28,8%** |

**Vì sao chưa chốt.** Mọi ước lượng điểm đều dương, hai cách diễn đạt độc lập
cùng chiều, và A đạt kết quả cao hơn **với ít vị thế hơn** (3,27 so với 4,00)
— tức lợi nhuận trên mỗi đồng phơi nhiễm tốt hơn hẳn. Nhưng **cả hai KTC95
đều chứa 0**, nghĩa là ở mức 95% chưa phân biệt được với may rủi, chưa nói
tới ngưỡng Šidák đã hiệu chỉnh. Đây là **2 ô mới** trong kế toán đa phép thử.

Một biến thể thắng vài chục bps với khoảng tin cậy chứa 0 là **một ô nữa
trong lưới tìm kiếm**, không phải một phát hiện.

**Trạng thái: đã chốt.** Tham số `xsmom.ma = 30` là mặc định trong hệ chạy
thật. Bản hiện thực là **cách A** (bỏ hẳn ứng viên không qua lọc, không thay
bằng mã kế tiếp) vì đó là nghĩa đen của luật; cách B cần thêm logic chọn lại
và không được hiện thực.

**Chốt với mức bằng chứng nào — ghi rõ để sau này không hiểu nhầm.** Quyết
định chốt là **lựa chọn vận hành**, không phải kết luận thống kê. KTC95 của
phần cải thiện **chứa 0**. Ba thứ đỡ cho quyết định này:

1. **Nhất quán** — hai cách diễn đạt độc lập (A và B) cùng dương, 5/6 năm
   dương, 6/7 sổ lệch ngày có bps cao hơn.
2. **Cơ chế đọc được** — hai cột loại ↑ / loại ↓ đảo chiều đúng theo chế độ
   thị trường (2022 chặn 217 lệnh mua, 2023 chặn 154 lệnh bán). Đó là dấu
   hiệu của một luật có cơ chế, không phải một tham số dò ra.
3. **Lợi ích rơi vào rủi ro, không vào tỷ lệ thắng** — % kỳ dương gần như
   không đổi, nhưng **đợt âm khỏi đỉnh dài nhất rút từ 660 xuống 493 ngày**
   (21,7 → 16,2 tháng). Đó là điểm yếu lớn nhất của chiến lược này, và bộ
   lọc đánh thẳng vào nó.

**Một chỗ phải nói ngược lại:** sụt của **từng sổ riêng lẻ** phần lớn **tệ
hơn** khi bật lọc (sổ 4: 39,3% → 55,1%; sổ 3: 46,8% → 53,7%). Chỉ sụt của
**bản gộp** giảm (45,7% → 44,1%). Lý do: bộ lọc cắn vào các sổ ở những thời
điểm khác nhau nên bảy sổ bớt tương quan — lợi ích nằm ở chỗ gộp, không ở
từng sổ. Ai chạy một sổ đơn lẻ thì bộ lọc này **làm xấu đi**.

Kiểm trên dữ liệu thật ngày 2026-10-25: `ma=0` cho 4 vị thế
(QNT↑ PUMP↑ SOL↓ DOGE↓), `ma=30` loại **cả hai chân mua** và còn lại
SOL↓ DOGE↓.

Script: `scripts/xsmom_ma_filter.py`.

## Lưới độ dài MA — vì sao dừng ở 30

Luật quyết **tuyên bố trước khi nhìn kết quả**: đổi khỏi MA30 chỉ khi độ dài
khác vừa cho CAGR/sụt cao hơn, **vừa** có KTC đã hiệu chỉnh Šidák (7 ô →
99,27%) không chứa 0. Lưới dùng 7 độ dài tiêu chuẩn, **không quét mịn** —
quét mịn là cách nhanh nhất để khớp nhiễu.

| MA | loại ↑ | loại ↓ | vt/kỳ | bps/kỳ | Vốn gộp | Sụt | **CAGR/sụt** | Âm dài nhất |
|---|---|---|---|---|---|---|---|---|
| tắt | — | — | 4,00 | +134,4 | 21,49× | 45,7% | 1,43 | 660 ngày |
| 10 | 38,0% | 32,6% | 2,61 | +81,4 | 5,08× | 40,2% | 0,76 | 509 |
| 14 | 33,4% | 28,7% | 2,76 | +98,5 | 12,75× | **37,1%** | 1,39 | **493** |
| 20 | 26,9% | 23,7% | 2,99 | +119,8 | 19,21× | 43,0% | 1,45 | 507 |
| **30** | 18,4% | 18,1% | 3,27 | +143,3 | **26,79×** | 44,1% | **1,61** | **493** |
| 50 | 11,8% | 18,5% | 3,39 | **+143,9** | 26,16× | 46,3% | 1,52 | 656 |
| 100 | 14,1% | 28,2% | 3,15 | +132,1 | 17,40× | 55,5% | 1,07 | 692 |
| 200 | 19,0% | 33,8% | 2,94 | +111,2 | 9,71× | 50,9% | 0,88 | 720 |

So cặp với MA30, KTC 99,27% đã hiệu chỉnh:

```
MA10   −63,8 bps/kỳ   [−125,1 ;  −11,0]   CAGR/sụt 0,76
MA14   −44,1 bps/kỳ   [−113,8 ;   +4,9]            1,39
MA20   −23,5 bps/kỳ   [ −82,2 ;  +12,0]            1,45
MA50    +0,6 bps/kỳ   [ −27,7 ;  +29,6]            1,52
MA100  −11,2 bps/kỳ   [ −58,8 ;  +33,6]            1,07
MA200  −32,0 bps/kỳ   [ −83,1 ;  +18,4]            0,88
```

**Kết luận: giữ MA30.** Không độ dài nào cho CAGR/sụt cao hơn 1,61, nên điều
kiện thứ nhất đã trượt và điều kiện thứ hai không cứu được.

**Hình dạng của lưới mới là phần đáng tin.** CAGR/sụt đi lên đều từ MA10
(0,76) qua MA20 (1,45) tới MA30 (1,61) rồi xuống đều qua MA50 (1,52), MA100
(1,07), MA200 (0,88) — một đường **đơn đỉnh, trơn**, cực đại đúng tại độ dài
đã chọn vì lý do cấu trúc (trùng cửa sổ chấm điểm 30 ngày). Nếu MA30 thắng
sít sao giữa một bảng răng cưa thì mới là dấu hiệu khớp nhiễu.

Hai cái bẫy trong bảng này:

**MA50 gần bằng về bps** (+143,9 so với +143,3, hiệu +0,6 với KTC chứa 0 —
không phân biệt được) nhưng **đợt âm dài 656 ngày** so với 493 của MA30, tức
mất sạch phần cải thiện đáng giá nhất. Chọn theo bps sẽ chọn nhầm.

**MA14 cho sụt thấp nhất** (37,1%) nhưng vốn chỉ 12,75× vì nó loại tới một
phần ba ứng viên. Ai ưu tiên êm hơn lợi nhuận thì đó là lựa chọn hợp lệ,
nhưng CAGR/sụt 1,39 vẫn thua MA30.

Lưới này cộng **7 ô** vào kế toán đa phép thử. Script:
`scripts/xsmom_ma_grid.py`.

## Ghi sổ theo đơn vị R

Từ 26/10/2026 cả kho ghi sổ theo [đơn vị R](money-management-r.md). Chiến
lược này **không có stop**, nên R được định nghĩa bằng biến động:

```
σ_kỳ = độ lệch chuẩn lợi suất log 30 ngày × √7     ← rủi ro một kỳ nắm giữ
R    = lợi suất ròng của vị thế / σ_kỳ
```

1R = một lần độ lệch chuẩn bất lợi qua đúng kỳ nắm giữ. Mẫu số **không phải
luật mới**: σ chính là mẫu số đã dùng ở bước chấm điểm.

**R trung bình +0,058 · thắng 50,1% · tổng +466R trên 8.076 vị thế.**

Đặt cạnh RSI(2) (+0,081R, thắng 73,7%) thì thấy hai cơ chế khác hẳn nhau:
chiến lược này **thắng đúng một nửa số lần** nhưng lần thắng lớn hơn lần
thua, còn RSI(2) thắng thường xuyên với biên rất mỏng. Chỉ thang R mới đặt
được hai thứ đó lên cùng một thước.

### Định cỡ vẫn CHIA ĐỀU, không theo R

Đã thử lấy σ làm trọng số (nghịch biến động). Nó **kém hơn chia đều**:

| phân bổ | Vốn gộp | Sụt | Phơi nhiễm TB | CAGR/sụt |
|---|---|---|---|---|
| **chia đều** | **21,49×** | 45,7% | 1,00× | **1,43** |
| rủi ro 1%/vị thế | 1,86× | 15,0% | 0,32× | 0,71 |
| rủi ro 3% | 5,76× | 30,2% | 0,77× | 1,10 |
| rủi ro 5% | 9,35× | 40,2% | 0,92× | 1,10 |
| rủi ro 8% | 13,64× | 47,2% | 0,97× | 1,13 |

Cột cuối **tăng đơn điệu** khi vặn rủi ro lên, và lý do nằm ở trần 25% mỗi vị
thế: risk% càng cao thì càng nhiều vị thế chạm trần, mà **bốn vị thế cùng
chạm trần 25% chính là chia đều**. Dữ liệu đang nói "càng giống chia đều càng
tốt" — nên giữ chia đều.

Nguyên nhân: chiến lược **đã chia cho σ ở bước chấm điểm**. Lấy σ làm trọng
số lần nữa là tính hai lần, và nó kéo danh mục về nhóm biến động thấp, trong
crypto là nhóm vốn hoá lớn — nhóm trả ít động lượng nhất.

Một ghi nhận ngược chiều, để không bỏ sót: định cỡ theo rủi ro **êm hơn hẳn
trong năm xấu**.

```
          chia đều            rủi ro 3%
2022      0,75×  sụt 41,0%    0,98×  sụt 23,9%
2026      1,70×  sụt 32,3%    1,14×  sụt 16,6%
```

Ai ưu tiên ngủ ngon hơn vốn cuối thì đây là đánh đổi có thật. Nhưng hạ phơi
nhiễm của chính bản chia đều xuống còn rẻ hơn: ở cùng mức sụt 30%, chia đều
giảm tỷ trọng vẫn cho khoảng 8,9× so với 5,76×.

## Kết quả từng năm — bản gộp 7 sổ

Bản **đã chốt (có lọc MA30)** đặt cạnh bản không lọc:

| Năm | Vốn năm | Sụt | bps/kỳ | % kỳ + | vt/kỳ | loại ↑ | loại ↓ | *(không lọc)* Vốn | Sụt |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | **3,24×** | **22,7%** | +362,0 | 55,0% | 3,20 | 96 | 119 | 3,11× | 27,7% |
| 2022 | 0,78× | **34,8%** | −30,0 | 49,6% | 3,16 | **217** | 88 | 0,75× | 41,0% |
| 2023 | 1,65× | 34,8% | +102,6 | 55,9% | 3,38 | **72** | 154 | 1,64× | 32,2% |
| 2024 | 2,01× | 26,4% | +169,6 | 61,7% | 3,25 | 109 | 164 | **2,13×** | 25,9% |
| 2025 | **1,78×** | **20,0%** | +126,2 | 54,8% | 3,20 | 184 | 109 | 1,57× | 25,1% |
| 2026 | **1,81×** | 33,5% | +198,4 | 47,8% | 3,44 | 65 | 98 | 1,70× | 32,3% |

Có lọc thắng **5/6 năm** về vốn và **5/6** về bps/kỳ; thua đúng 2024 — năm
bản gốc chạy đúng nhất (64,8% kỳ dương). Khi luật gốc đang đúng thì mọi bộ
lọc đều chỉ có thể làm tệ đi; đó là cái giá cố hữu của việc thêm điều kiện
chặn, không phải điểm yếu riêng của MA30.

**Cách nó cải thiện không phải bằng đoán đúng hơn.** % kỳ dương gần như đứng
yên, có năm còn giảm. Lợi ích nằm ở **độ lớn**: những lần sai nhỏ lại — thấy
rõ ở cột sụt (2021 −5,0 điểm, 2022 −6,2 điểm, 2025 −5,1 điểm).

**Hai cột loại ↑ / loại ↓ đảo chiều theo chế độ thị trường.** Mùa gấu 2022
chặn 217 lệnh mua và chỉ 88 lệnh bán; năm hồi phục 2023 đảo ngược hoàn toàn
(72 mua, 154 bán). Bộ lọc tự nhận ra chế độ mà không ai phải bảo nó.

Chỉ 2022 lỗ, và **cả bảy sổ đều lỗ năm đó** — đó là chế độ thị trường, không
phải may rủi lưới ngày.

Một sổ đơn lẻ (vào lệnh thứ Sáu) theo năm, bps/kỳ: 2021 **+283** · 2022 −13 ·
2023 +95 · 2024 **+173** · 2025 +61 · 2026 **+174**. Hai chân luân phiên gánh
nhau: 2022 chân mua −364 nhưng chân bán +337; 2025 chân mua −6 nhưng chân bán
+129. Rổ đều toàn kỳ chỉ +3 bps — **không phải beta**.

## Bảy sổ

Nhãn thứ dưới đây là **ngày VÀO LỆNH** (ngày chốt điểm là hôm trước).

Số dưới đây là **bản đã chốt, có lọc MA30**.

| Sổ | Vào lệnh | bps/kỳ | KTC95 | Vốn | Sụt/ngày | % kỳ + |
|---|---|---|---|---|---|---|
| 0 | thứ Sáu | +120,7 | [+30,4 ; +214,3] | 9,13× | 52,0% | 52,6% |
| 1 | thứ Bảy | +130,4 | [+46,9 ; +218,2] | 13,66× | 57,1% | 51,2% |
| 2 | Chủ nhật | +169,8 | [+75,8 ; +270,4] | 45,81× | 52,2% | 57,1% |
| 3 | thứ Hai | +156,4 | [+69,0 ; +253,1] | 33,81× | 53,7% | 54,9% |
| 4 | thứ Ba | **+170,9** | [+69,9 ; +277,0] | **54,72×** | 55,1% | 54,5% |
| 5 | thứ Tư | +132,3 | [+40,2 ; +222,1] | 18,75× | **51,1%** | 55,9% |
| 6 | thứ Năm | +122,6 | [+12,6 ; +237,1] | 11,64× | 55,9% | 54,2% |

**Cả bảy sổ dương, cả bảy KTC95 không chạm 0.** Gộp 7 sổ: **26,79×**, dải
từng sổ **9,13× – 54,72×**.

Bản không lọc để đối chiếu:

| Sổ | Vào lệnh | bps/kỳ | KTC95 | Vốn | Sụt/ngày |
|---|---|---|---|---|---|
| 0 | thứ Sáu | +120,0 | [+32,3 ; +215,6] | 9,30× | 51,9% |
| 1 | thứ Bảy | +126,2 | [+40,0 ; +219,2] | 12,35× | 54,2% |
| 2 | Chủ nhật | +157,9 | [+68,0 ; +260,6] | 34,95× | 46,3% |
| 3 | thứ Hai | +129,3 | [+43,2 ; +226,1] | 16,45× | 46,9% |
| 4 | thứ Ba | **+168,0** | [+75,6 ; +268,8] | **52,65×** | **39,3%** |
| 5 | thứ Tư | +105,9 | [+15,0 ; +196,8] | 8,51× | 61,0% |
| 6 | thứ Năm | +133,7 | [+19,4 ; +248,7] | 16,27× | 60,1% |
| **gộp** | **cả bảy** | **+134,4** | độ lệch 21,6 | **21,22×** | **45,8%** |

**7/7 sổ dương, 7/7 khoảng tin cậy loại 0.** Gộp 7 sổ **không** làm sụt vốn nhỏ
đi (45,8% nằm giữa dải 39,3–61,0%) — bảy sổ tương quan rất mạnh vì cùng một
tín hiệu. Chia lệch ngày khử nhiễu **thời điểm**, không khử **rủi ro gốc**.

## Thời gian âm khỏi đỉnh

Đây là chỉ số quan trọng nhất về mặt chịu đựng, và nó tệ hơn con số sụt vốn.
Một "đợt âm" tính từ ngày lập đỉnh tới ngày **vượt lại chính đỉnh đó**.

**Bộ lọc MA30 rút đợt dài nhất từ 660 xuống 493 ngày** — từ 21,7 tháng còn
16,2 tháng. Đây là cải thiện đáng giá nhất của bộ lọc, vì đợt chìm dài là
điểm yếu lớn nhất của chiến lược.

Bảng dưới đây là **bản KHÔNG lọc** (chưa dựng lại chi tiết từng đợt cho bản
có lọc; chỉ đợt dài nhất đã đo lại là 493 ngày). Bản gộp 7 sổ, chân trời
30 ngày — sáu đợt dài nhất:

| Đỉnh cũ | Đáy | Lập đỉnh mới | Dài | Sâu nhất |
|---|---|---|---|---|
| 2022-01-17 | 2023-08-26 | 2023-11-09 | **661 ngày · 21,7 tháng** | 45,8% |
| 2025-02-27 | 2025-07-21 | 2025-10-12 | 227 ngày · 7,5 tháng | 25,1% |
| 2021-05-27 | 2021-07-10 | 2021-09-03 | 99 ngày | 27,7% |
| 2024-06-09 | 2024-07-20 | 2024-09-11 | 94 ngày | 21,1% |
| 2025-12-26 | 2026-03-05 | 2026-03-23 | 87 ngày | 24,4% |
| 2023-12-25 | 2024-01-21 | 2024-03-10 | 76 ngày | 18,9% |

**61 đợt · dài nhất 661 ngày · trung vị 6 ngày · 94% số ngày ở dưới đỉnh.**
Đợt dài nhất cũng chính là đợt sâu nhất. Chân trời 90 ngày tương tự: dài nhất
**573 ngày (18,8 tháng)**, 95% số ngày dưới đỉnh.

**Một sổ đơn lẻ còn tệ hơn nhiều** — đây là lý do nữa để chạy đủ bảy sổ:

| Sổ (30 ngày) | Đợt dài nhất | Sâu của đợt đó | Khoảng |
|---|---|---|---|
| thứ Ba | 570 ngày · 18,7 tháng | 39,3% | 2022-04-01 → 2023-10-23 |
| thứ Hai | 615 ngày · 20,2 tháng | 46,9% | 2022-04-01 → 2023-12-07 |
| thứ Sáu | 645 ngày · 21,2 tháng | 37,1% | 2022-01-17 → 2023-10-24 |
| Chủ nhật | 689 ngày · 22,6 tháng | 46,3% | 2022-01-17 → 2023-12-07 |
| thứ Bảy | 706 ngày · 23,2 tháng | 54,2% | 2022-01-17 → 2023-12-24 |
| thứ Năm | 794 ngày · 26,1 tháng | 60,1% | 2022-01-17 → 2024-03-21 |
| **thứ Tư** | **898 ngày · 29,5 tháng** | **61,0%** | 2021-11-29 → 2024-05-15 |

Chạy đúng một sổ và lỡ chọn thứ Tư là **chìm gần hai năm rưỡi**. Gộp bảy sổ
rút xuống 661 ngày, và thêm bộ lọc MA30 rút tiếp còn **493 ngày** — vẫn dài,
nhưng là mức có thể nói trước được.

## Ba phép kiểm nó đã vượt

Ba phép kiểm dưới đây chạy trên **bản KHÔNG lọc**. Chúng là nền tảng thống kê
của chiến lược; bộ lọc MA30 chốt thêm lên trên và **không** thừa hưởng các
kết quả này. Xem § "Bộ lọc MA30" cho mức bằng chứng riêng của nó.

**1 · Hoán vị thứ hạng.** Giả thuyết không đúng cho chiến lược xếp hạng không
phải "thị trường đi lên" mà là **xáo thứ hạng trong từng ngày** — giữ nguyên
ngày, kích thước danh mục, phân phối lợi suất chéo; chỉ phá liên kết giữa tín
hiệu và lợi suất. Kết quả: z từ **+3,34 đến +5,19** trên cả bảy sổ, p hai phía
dưới ngưỡng phân giải ở mọi sổ.

**2 · Bỏ hẳn năm gần nhất.** 5/10 kỳ lãi nhất của bản *thô* nằm ở 2026, nên
phải loại trừ khả năng "đây là chuyện của 10 tháng cuối". Chạy lại chỉ trên
**2021–2025** (1.500 hoán vị): **+111,1 bps/kỳ · KTC95 [+30,2 ; +205,0] ·
7,67× · z = +3,63 · vượt ngưỡng Šidák**. Bản thô rụng từ 8,04× xuống 2,89×
khi bỏ 2026; bản chia biến động thì không.

**3 · Dịch lưới tái cân bằng.** Bẫy đã sập một lần ở
[dòng tiền cưỡng bức](dong-tien-cuong-buc.md): lưới bước cố định làm mọi kỳ
rơi vào cùng một thứ, và khi đó không phân biệt được lợi thế thật với nếp
lịch. Dịch 0–6 ngày phủ hết bảy thứ: **7/7 dương**, và lưới gốc (thứ Sáu,
+120,0) còn **dưới trung bình** (+134,4) — nếu có thiên lệch thì nó đang báo
thiếu.

## Thô so với chia biến động

Cùng top 20, cùng cách đo:

| | Sụt (mốc tái cân bằng) | Số năm dương | Vốn | Bỏ 2026 còn |
|---|---|---|---|---|
| Động lượng **thô** 90n | 63,3% | 4/6 | 8,04× | 2,89× |
| **Chia biến động** 90n | **45,1%** | **6/6** | 7,26× | — |
| **Chia biến động** 30n | 50,1% | 5/6 | **9,30×** | **7,67×** |

Mười kỳ lãi nhất phân bố theo năm:

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| chia biến động 90n | 2 | **1** | 1 | 1 | **1** | 4 |
| thô 90n | 2 | 0 | 2 | 1 | 0 | **5** |

Bản chia biến động có ít nhất một kỳ vàng ở **mọi** năm; bản thô trống hẳn
2022 và 2025.

## Nó thực sự mua bán cái gì

Vì vũ trụ là top 20 thanh khoản nên phần lớn là **mã lớn, vào được cỡ lớn** —
không phải micro-cap. Sổ thứ Sáu, chân MUA 100 mã khác nhau: XRP(28), BTC(27),
BNB(22), SOL(21), DOGE(16), ZEC(16), AAVE(15), NEAR(15). Chân BÁN 73 mã:
XRP(38), DOGE(38), ADA(31), ETH(29), BTC(27), SOL(22). XRP và DOGE xuất hiện ở
**cả hai chân** — chiến lược xoay chiều chúng theo xu hướng.

Xen vào đó là token mới đang nóng (LAB, AKE, PUMP, HYPE, SIREN): chúng lọt
top 20 thanh khoản thật, vì khối lượng lúc mới niêm yết rất lớn.

## Frog-in-the-pan — đã thử 27/10/2026, LOẠI

Da, Gurun, Warachka (2014): động lượng đến từ **nhiều bước nhỏ đều** bền hơn
động lượng đến từ **vài cú giật lớn**. Đo bằng độ giật
`ID = %ngày ngược chiều − %ngày cùng chiều` trên đúng cửa sổ 30 ngày của điểm,
ký theo chiều chân (ID thấp = đi đều).

**Luật, đăng ký trước trong docstring script:** lấy họ 4 ứng viên mỗi chân
theo điểm, giữ 2 mã ID thấp nhất, rồi áp MA30 cách A y như bản chốt. Chốt
chỉ khi (1) nửa dò < 2024-07 có hiệu > 0, (2) nửa kiểm ≥ 2024-07 có KTC95
loại 0 phía dương, (3) CAGR/sụt toàn mẫu ≥ bản chốt.

| | vt/kỳ | bps/kỳ | Vốn gộp | Sụt | CAGR/sụt | Âm dài nhất |
|---|---|---|---|---|---|---|
| **bản chốt** | 3,27 | **+143,3** | **26,79×** | **44,1%** | **1,61** | **493 ngày** |
| ếch + MA30 | 3,23 | +118,2 | 16,27× | 54,8% | 1,06 | 848 ngày |

```
ếch − chốt   toàn mẫu  −25,1 bps/kỳ · KTC95 [ −68,0 ; +12,5] · 2.019 kỳ
             nửa dò    −26,4         · KTC95 [ −76,3 ;  +9,2]
             nửa kiểm  −23,3         · KTC95 [−101,8 ; +50,0]
```

**Trượt cả ba điều kiện → LOẠI.** Hiệu bps/kỳ âm 5/6 năm (chỉ dương 2025),
vốn thua 5/7 sổ. Bộ lọc không phải một cú đẩy nhẹ: nó đổi **70,2%** số chỗ so với bản chốt.

**Vì sao — và đây là phần đáng giữ.** Lợi suất 7 ngày theo hạng **điểm** trong
họ 4 mã, chân MUA, chưa phí:

```
hạng điểm   #1       #2      #3      #4
TB        +239,5   +60,1   +69,9   +20,3
trung vị  −138,1  −134,6   −64,5  −105,5
```

Mã đứng đầu bảng **trung bình +240 bps nhưng trung vị −138**: lợi thế chân
mua nằm gần hết ở đuôi phải của hạng #1, và đuôi đó thường đến từ **chính
những cú giật** mà bộ lọc ếch loại đi. Bộ lọc làm lệnh điển hình tốt lên
(trung vị hạng ID #1 là −50,5 so với −138,1) nhưng cắt mất đuôi. Đây là
cùng một bài học như chốt lời ở [dòng tiền cưỡng bức](dong-tien-cuong-buc.md)
§ Phần 3: **ở đây lợi thế chính là đuôi phải, cắt đuôi là mất lợi thế.**

Chẩn đoán trong họ (giữ − bỏ, theo chiều chân) cho **+63,2 bps**, KTC95
[−6,8 ; +134,6], tức ID có tách được một phần trong 4 ứng viên. Nhưng
"giữ tốt hơn bỏ" không phải "giữ tốt hơn bản chốt": bản chốt lấy hạng #1–#2
theo điểm, còn bộ lọc ếch hay đẩy hạng #1 ra ngoài.

Một quan sát **không được dùng để quyết**: ở chân BÁN, hạng ID #1 (+89,3)
tốt hơn hạng điểm #1 (+45,9), và trung vị cũng tốt hơn. Đọc ra từ sau khi đã
nhìn số. Muốn thử "ếch chỉ cho chân bán" thì phải coi đó là một ô mới trên
dữ liệu chưa dùng, không phải vớt lại ô này.

Script: `scripts/xsmom_frog.py` (tái tạo bản chốt khớp từng số trước khi so).

## Động lượng phần dư — đã thử 27/10/2026, LOẠI

Blitz, Huij, Martens (2011): xếp hạng theo phần lợi suất **không giải thích
được bởi thị trường** thay vì lợi suất thô. Giả thuyết: chân MUA đang chứa mã
beta cao, nên sập theo thị trường năm 2022.

**Luật, đăng ký trước:** cùng tập mã đủ điều kiện, chỉ đổi công thức điểm.
Thị trường = rổ đều top 20 (không phải BTC, vì phần dư của BTC với chính nó
bằng 0). β = OLS 90 ngày, `e = r − β·m` trên 30 ngày cuối, điểm =
`Σe / σ(e)`, **không** trừ hằng số. Luật quyết y hệt frog-in-the-pan.

| | vt/kỳ | bps/kỳ | Vốn gộp | Sụt | CAGR/sụt | Âm dài nhất |
|---|---|---|---|---|---|---|
| **bản chốt** | 3,27 | **+143,3** | **26,79×** | 44,1% | 1,61 | 493 ngày |
| phần dư + MA30 | 3,22 | +140,9 | 26,57× | **34,2%** | **2,08** | 493 ngày |

```
dư − chốt   toàn mẫu   −2,4 bps/kỳ · KTC95 [−47,8 ; +38,8] · 2.019 kỳ
            nửa dò    −25,9         · KTC95 [−90,1 ; +21,5]
            nửa kiểm  +30,7         · KTC95 [−21,3 ; +94,5]
```

**(1) trượt, (2) trượt, (3) đạt → LOẠI.** Đổi 54,8% số chỗ. Theo năm hiệu
bps/kỳ: 2021 **−160,5** · 2022 +31,2 · 2023 +8,3 · 2024 −35,0 · 2025 +6,6 ·
2026 **+118,4**. Vốn thắng 4/7 sổ.

**Vì sao không vớt lại bằng con số sụt 34,2%.** CAGR/sụt 2,08 là con số đẹp
nhất kho từng thấy cho chiến lược này, và đó chính là lý do phải nói rõ:

1. **Cơ chế đã đăng ký không xuất hiện.** Beta TB của mã được chọn, trước
   lọc MA30:

   ```
               MUA chốt  MUA dư  BÁN chốt  BÁN dư
   toàn mẫu      1,10     1,05     1,00     1,06
   2022          1,04     0,99     0,98     1,01
   ```

   Chân MUA của bản chốt **không** nghiêng về beta cao — 1,10 so với rổ đều
   trung bình 1,00, và năm 2022 còn là 1,04. Mẫu số σ trong điểm `ret/σ` đã
   phạt sẵn mã biến động mạnh, tức đã làm phần lớn việc mà phần dư định làm.
   Giả thuyết "2022 thua vì beta" **sai**.
2. **Sụt tối đa là một con số của một đường đi.** Nó đo đúng một đợt tệ
   nhất; không có cơ chế đọc được đứng sau thì nó không khác một lần rút may.
3. **Hiệu đổi dấu giữa hai nửa** (−25,9 rồi +30,7) và dồn vào hai năm đầu
   cuối (2021 −160, 2026 +118) — hình dạng của nhiễu theo thời gian, không
   phải của một cải thiện đều.

Muốn kiểm lại câu "phần dư sụt nhẹ hơn" thì mẫu sạch duy nhất còn lại là
**dữ liệu chạy thật từ 27/10/2026 trở đi**, và phải tuyên bố trước con số sụt
nào thì đổi.

Script: `scripts/xsmom_resid.py`.

## Nhồi lệnh — 28/10/2026, KHÔNG THAY (nhồi ngược là ứng viên yếu)

Engine của tab «Tính lịch sử» (khoá nghiên cứu `xadd`). Lớp gốc giữ nguyên bộ
đang chạy. Mỗi ngày, với mỗi lớp gốc đang giữ: **thuận** — lời từ lớp gần
nhất ≥ d×σ ngày; **ngược** — lỗ ≥ d×σ ngày → thêm một lớp ở open hôm sau,
cỡ = lớp gốc × hệ số; lớp thêm đóng cùng lớp gốc. Lưới 18 ô: chiều × d 1/2/3
× {1 lớp ×1, 2 lớp ×1×1, 2 lớp ×2×4}. Động lượng riêng (ALLOC_RSI2 = 0),
1R = 100, không trần. Script `scripts/xsmom_add.py`, luật trong docstring.

| | R/năm | sụt R | Sharpe | 2022 |
|---|---|---|---|---|
| **gốc** | +96 | 109 | **0,91** | −14,9 |
| thuận d1, 1 lớp | +173 | 145 | 0,98 | −21,0 |
| thuận d1, 2 lớp ×2×4 | +402 | 497 | 0,84 | −99,4 |
| **ngược d1, 1 lớp** | +160 | 117 | **1,14** | −15,5 |
| ngược d1, 2 lớp | +185 | 135 | 1,21 | −3,8 |
| ngược d1, 2 lớp ×2×4 (ô chọn) | +324 | 274 | 1,31 | +30,6 |
| ngược d2, 1 lớp | +133 | 110 | 1,09 | +1,9 |
| ngược d3, 1 lớp | +109 | 107 | 0,97 | −4,3 |

- **Nhồi thuận** làm R/năm to lên nhưng Sharpe gần như không đổi, còn bản
  gấp đôi thì tệ hơn (0,84) và sụt gấp 4,5 lần — chỉ là phơi nhiễm lớn hơn.
- **Nhồi ngược dương ở cả 9/9 ô** (Sharpe 0,97–1,31), tốt hơn gốc 5/6 năm ở
  ô chọn. Nhưng KTC Bonferroni 18 ô của chênh Sharpe là [−0,54 ; +1,28] —
  **trượt (1), không thay.**

**Phép giả — nhồi ở thời điểm ngẫu nhiên, cùng tần suất:** Sharpe trung bình
**0,99** (5 lần rút, dải 0,87–1,10). Tức là khoảng một nửa phần cải thiện chỉ
là "cầm nhiều lớp hơn"; phần do *thời điểm* (giá đi ngược thì thêm) là
+0,10–0,22 Sharpe so với giả, nằm ở mép trên dải giả:

| ô | Sharpe | KTC95 chênh so với gốc | giả ngẫu nhiên TB |
|---|---|---|---|
| ngược d1, 1 lớp | 1,14 | [−0,05 ; +0,47] | 0,99 |
| ngược d2, 1 lớp | 1,09 | [−0,06 ; +0,38] | 0,95 |
| ngược d1, 2 lớp | 1,21 | [−0,07 ; +0,63] | 0,99 |

Hướng của nó khớp với một điều đã biết: lợi thế động lượng nằm ở đuôi phải
và đường đi trong tuần nhiễu — mua thêm khi một mã thắng điều chỉnh là mua
rẻ hơn cùng một lợi thế. Nhưng chưa chứng minh được, và chưa được chấm trên
6 cách cắt ngày (engine đọc nến D cắt 00:00). **Ứng viên cho sổ giấy, không
phải cho tiền thật.**

## Lệnh nhồi có khung riêng ±1 ATR — 28/10/2026, XÁC NHẬN cho sổ giấy

Ý của người vận hành: lệnh gốc giữ nguyên; khi giá đã đi **đúng chiều 1 ATR**
so với giá vào, mở thêm một lệnh nhồi có **chốt lời +1 ATR, cắt lỗ −1 ATR**
riêng. Câu hỏi chỉ còn: bản thân lệnh nhồi có kỳ vọng dương không?

**Bước 1 — lưới** (`scripts/add_bracket.py`): kích hoạt t 0,5/1/1,5 ATR × khung
b 0,5/1/1,5 ATR × tối đa N 1/3 lệnh nhồi × độc lập / đóng cùng lệnh gốc, trên
lệnh thật của engine (ALLOC 8/1), cùng ngày chạm cả hai → tính cắt lỗ. 72 ô.

- **RSI(2): không có gì.** Ô người dùng 45 lệnh nhồi, +0,005R. RSI(2) thoát
  trước khi giá kịp đi xa; bản "đóng cùng lệnh gốc" gần như không có lệnh.
- **Động lượng: có.** Ô người dùng (1 / 1 / 1 / độc lập): 1.736 lệnh nhồi,
  thắng 55,0%, **+0,085R/lệnh**, dương 5/6 năm, **6/6 lân cận dương**. Khung
  0,5 ATR âm ở mọi ô (phí 10 bps ÷ khung hẹp + nhiễu), khung ≥ 1 ATR dương ở
  mọi ô. t 1,5 / b 1 / N 3: +0,103R, **dương cả 6 năm**.
- Trượt luật lưới: KTC Bonferroni 72 ô [−0,059 ; +0,247].

**Phép giả** — cùng khung ±1 ATR, vào ở ngày **ngẫu nhiên** trong lúc giữ lệnh
gốc, cùng số lệnh, 5 lần rút: **−0,016R** (dải −0,048 … +0,016). Tức là lợi
thế không đến từ "đứng cùng phía với một lệnh động lượng" mà từ **điểm kích
hoạt**: sau khi một mã động lượng đã đi đúng 1 ATR, xác suất đi tiếp thêm 1
ATR trước khi lùi 1 ATR là ~55%. Gộp vào động lượng: Sharpe 0,91 → 1,05.

**Bước 2 — phép xác nhận đăng ký trước, chỉ ô người dùng**
(`scripts/add_bracket_confirm.py`): nến D dựng từ nến 1H ở **6 cách cắt
ngày**, ATR trên chính nến đó, chạm chốt lời / cắt lỗ xét trên **nến 1H** (cùng
một giờ chạm cả hai → cắt lỗ). 102/134 mã có nến 1H.

| Cắt ngày | 0h | 4h | 8h | 12h | 16h | 20h |
|---|---|---|---|---|---|---|
| lệnh nhồi | 1.134 | 1.160 | 1.173 | 1.165 | 1.152 | 1.176 |
| thắng | 55,6% | 53,9% | 52,9% | 51,2% | 57,4% | 59,5% |
| **R/lệnh** | **+0,097** | +0,063 | +0,045 | +0,011 | +0,133 | +0,176 |

```
TB 6 cách cắt        +0,087 R/lệnh
phép giả mốc 0h      −0,003 (5 lần: −0,011 +0,000 −0,005 −0,064 +0,072)
thật − giả           +0,099 · KTC95 [+0,006 ; +0,195]
mốc 0h theo năm R    +21 · +29 · +11 · +24 · +19 · +6   (dương cả 6 năm)
```

**Đạt cả ba điều kiện → XÁC NHẬN, là ứng viên cho sổ giấy.** Đây là kết quả
đầu tiên trong cả chuỗi nghiên cứu sau RSI(2) và động lượng qua được một phép
xác nhận đăng ký trước. Nó **không** phải chiến lược độc lập: nó sống bên
trong động lượng (chỉ nhồi vào mã đang được động lượng giữ, đúng chiều).

Giới hạn còn lại:

- Bằng chứng mỏng ở mốc 12h (+0,011); KTC của phần hơn phép giả chỉ vừa loại
  0 (+0,006).
- Thực thi khác backtest: cần **lệnh chốt lời / cắt lỗ đặt sẵn trên sàn**
  (TAKE_PROFIT_MARKET / STOP_MARKET, reduceOnly đúng khối lượng lớp nhồi) — bot
  hiện chỉ chạy một lần mỗi ngày và chưa đặt lệnh chờ nào. Trượt giá của lệnh
  stop chưa tính.
- Rủi ro mỗi lệnh nhồi 1R = 1 ATR — cỡ lệnh lớn hơn lớp gốc nhiều lần nếu
  dùng cùng 1R; phải chọn hệ số riêng khi chạy thật.

## Những gì đã thử và KHÔNG được

Hai đợt sàng lọc, **36 ô cắt ngang** cộng 6 ô theo-từng-lệnh:

| Họ | Kết quả |
|---|---|
| Bám xu hướng toàn vũ trụ (Donchian 20/10, 55/27, EMA 10/30) | **Chết.** KTC trùm 0, tài khoản mất 65–89%. Xác nhận lại kết luận cũ, lần này trên 623 mã thay vì riêng BTC |
| Stat-arb theo cặp (tương quan trượt 90n, z-score) | **Chết.** −44 đến −78 bps/lệnh, KTC loại 0 **về phía âm** |
| Carry funding (bán nhóm funding cao, mua nhóm âm) | 1/6 ô qua. Chưa đủ chốt. Không mâu thuẫn với kết quả âm đã biết: ở kia funding là *đặc trưng dự báo*, ở đây là *dòng tiền* |
| Ưa vé số (MAX 30 ngày) | **Không có.** \|z\| lớn nhất 0,42. Perp crypto không có phần bù vé số |
| Biến động thấp (30n, 90n) | **Không có.** \|z\| lớn nhất 1,58 |
| Beta thấp với BTC | **Không có.** \|z\| lớn nhất 0,65. Betting-against-beta vắng mặt |
| Sốc khối lượng | Trượt Šidák (p 0,028). Dấu của nó là *khối lượng cao thì tốt hơn* |
| Đảo chiều cắt ngang 7 ngày | Không có (p 0,057) |
| Đảo chiều cắt ngang 14 ngày | Dấu **NGƯỢC** — tức mua mã tăng mạnh 14 ngày. Giả thuyết "RSI(2) có bản cắt ngang" bị bác |
| Mở rộng vũ trụ (top 50 / 100 / 200) | KTC chứa 0 ở mọi cấu hình |
| Mở rộng danh mục (20% / 30% / 40% mỗi chân) | KTC chứa 0 ở mọi cấu hình |
| Frog-in-the-pan (chọn 2/4 theo độ giật), 27/10/2026 | **Loại.** −25,1 bps/kỳ, CAGR/sụt 1,06 so với 1,61. Cắt mất đuôi phải của hạng #1 |
| Động lượng phần dư (β 90 ngày với rổ đều top 20), 27/10/2026 | **Loại.** −2,4 bps/kỳ, nửa dò −25,9. Sụt 34,2% nhưng cơ chế beta không xuất hiện |
| Bán khống perp mới niêm yết (615 sự kiện, giữ 30 ngày), 27/10/2026 | **Loại.** Trung vị giá −21% nhưng TB ròng −116 bps — đuôi bơm ×5–×34 ăn hết. Xem `niem-yet-moi.md` |
| Dữ liệu ngoài: TVL (DefiLlama), tỉ lệ khối lượng perp/spot, cung stablecoin, 27/10/2026 | **Loại cả ba.** Perp/spot sát nút (+62 bps/kỳ) nhưng đo bằng khối lượng Bybit thì về 0 (+1,4) — không phải hiệu ứng đầu cơ chung. Xem `du-lieu-ngoai.md` |
| Giao dịch trong ngày: 1H (động lượng trong ngày, phá vỡ biên độ, mùa vụ giờ, đảo chiều sau sốc) + 15 phút (momentum vùng nhiễu, ORB đầu phiên, BTC dẫn altcoin, mùa vụ thứ × phiên), 27/10/2026 | **Loại cả tám họ** (158 ô). Trước phí ≈ 0 ở 15 phút; ô dương ở 1H đều chỉ mua. Xem `trong-ngay.md` |
| Nhồi lệnh thuận / ngược trên động lượng, 28/10/2026 | **Không thay.** Thuận chỉ là phơi nhiễm lớn hơn; ngược tốt hơn ở 9/9 ô (Sharpe 0,91 → 1,14) nhưng KTC chứa 0 và một nửa là hiệu ứng cầm nhiều lớp hơn |
| Lệnh nhồi có khung ±1 ATR sau khi giá đi đúng 1 ATR, 28/10/2026 | **Xác nhận cho sổ giấy.** +0,087R/lệnh TB 6 cách cắt ngày, phép giả −0,003; RSI(2) thì không có gì |
| Bán khống sau tin huỷ niêm yết của Binance (gỡ spot, gỡ perp, thẻ Monitoring), 28/10/2026 | **Loại cả ba** (72 ô). Gỡ spot: +693 bps/lệnh, vượt phép giả, nhưng KTC chứa 0 — 7/67 lệnh lỗ > 50% do ép bán khống; phần rơi lớn nhất (−19%) nằm trong ngày thông báo. Bản nến 1 phút (96 ô): phút đầu sau tin đã rơi −11%, phần trôi 24 giờ còn +400 … +700 bps nhưng KTC vẫn chứa 0. Bản aggTrades (144 ô): **thẻ Monitoring đạt** (+650 bps, giữ 24 giờ, trễ không quan trọng) → ứng viên sổ giấy. Stop dời theo lời (108 ô): **tin gỡ spot đạt** nếu vào trong ~1 giây. Đổi lại: bot **chặn mua** mã có tin. Xem `huy-niem-yet.md` |
| Stop ở đỉnh/đáy cũ (pivot, Donchian, ZigZag, nổi bật) cho lệnh nhồi, lệnh gốc động lượng và RSI(2), 28/10/2026 | **Không hơn stop đang dùng ở cả ba chỗ** (96 ô). Volume profile (96 ô): stop HVN cho RSI(2) đạt luật nhưng phần lớn là cỡ lệnh to hơn, Sharpe chênh KTC chứa 0. Xem `stop-dinh-day.md` |

**Quan trọng:** ba thứ *có* tín hiệu — chia biến động, động lượng 14 ngày (đảo
dấu), sốc khối lượng (đảo dấu) — đều chỉ về **cùng một phía: mua cái vừa
tăng**. Chúng không phải ba khám phá độc lập mà là ba cách đo lại một hiệu
ứng.

## Bẫy đã sập và cách gỡ

1. **Lọc nhìn trước trong điều kiện đủ tư cách.** Bản đầu đòi giá ở ngày thoát
   phải tồn tại — thế là loại sạch mã sẽ huỷ niêm yết trong kỳ, đúng kiểu thiên
   lệch sống sót đã gặp ở RSI(2). Gỡ: mã chết thoát ở **giá cuối cùng có**.
2. **Giả thuyết không sinh số lệnh khác bản thật.** Ở họ bám xu hướng, phần
   sinh tín hiệu chạy lại trong mỗi lượt null nên luật "không chồng lấn lệnh"
   cho ra số lệnh khác. Việc này lật dấu z của Donchian 20/10 từ **−2,59 thành
   +0,48**. Gỡ: tách sinh-tín-hiệu khỏi chạy-lệnh, null dùng **đúng danh sách
   tín hiệu**, chỉ đổi nến vào.
3. **Lưới 7 ngày khoá vào một thứ.** Xem § "Ba phép kiểm", điểm 3.
4. **Không nhớ điểm số thì không chạy nổi.** 2.000 hoán vị × 300 ngày × 623 mã
   mà tính lại độ lệch chuẩn mỗi lần là hết giờ. Gỡ: tính trước vector điểm
   tại mọi ngày rồi tra bảng.

## Bội số phép thử — kế toán

| Nhóm | Số ô |
|---|---|
| Đợt 1 cắt ngang: động lượng thô (3 chân trời × 3 vũ trụ) + carry (2 × 3) | 15 |
| Đợt 2 cắt ngang: 6 họ × 1–2 chân trời × 3 vũ trụ | 21 |
| **Tổng cắt ngang** → ngưỡng Šidák α=0,05 | **36 ô · p < 0,00142** |
| Đợt 1 theo từng lệnh: bám xu hướng 3 + stat-arb 3 | 6 |
| Dịch lưới 7 × 3 biến thể | **xác nhận**, không dùng để chọn |
| Bỏ 2026 | **xác nhận**, không dùng để chọn |

Hai ô qua cửa Šidák: **chia biến động 30n** và **90n**, đều ở top 20. Lưu ý
các ô tương quan mạnh với nhau nên 36 không phải 36 phép thử độc lập — hiệu
chỉnh này **rộng rãi**, không chặt.

### Thêm ngày 26/10/2026 — đợt dò bộ lọc

| Nhóm | Số ô | Kết quả |
|---|---|---|
| Bộ lọc MA30, hai cách diễn đạt (A bỏ lệnh · B lọc trước) | 2 | **đã chốt A** — KTC chứa 0 |
| Lọc RSI: RSI(2), RSI(14), RSI(14)+MA30 | 3 | **loại** — KTC không chứa 0, phía thiệt hại |
| Lưới độ dài MA: 10/14/20/30/50/100/200 | 7 | giữ MA30 |
| Cửa sổ thanh khoản 10 ngày (so với 30) | 1 | giữ 30 ngày |
| **Cộng thêm** | **13 ô** | |

Tổng cắt ngang lên **49 ô**, ngưỡng Šidák chặt lại còn **p < 0,00105**.

Phải nói thẳng một điều: **đợt dò này làm khó chính MA30.** Mười ba ô mới đều
cộng vào cùng một mẫu, nên bất kỳ phát hiện nào sau này trên mẫu đó đều phải
vượt ngưỡng chặt hơn. Nếu còn muốn thử nhiều biến thể nữa, cách đúng là tách
riêng một giai đoạn dò tìm có tuyên bố trước rồi kiểm định phần thắng trên dữ
liệu chưa dùng, thay vì cộng dồn mãi vào đây.

### Thêm ngày 27/10/2026 — đợt thanh khoản

| Nhóm | Số ô | Kết quả |
|---|---|---|
| Phi thanh khoản Amihud, hai phía | 1 | **loại** — KTC chứa 0 cả hai chiều |
| Sốc khối lượng trên top-50 | 0 | **tái lập** ô đã có ở bảng trên (p 0,028, cùng dấu) |
| **Cộng thêm** | **1 ô** | |

Tổng cắt ngang lên **50 ô**, ngưỡng Šidák **p < 0,00102**. Xem
`docs/thanh-khoan.md` — đợt đó cũng đo chi phí thanh khoản thật của chính
chiến lược này: ở 1R = 100 USD trượt giá là **0,01 bps** (mốc 95%: 0,08 bps),
nên phí 10 bps không bỏ sót gì, và trần công suất là **1R ≈ 10.000 USD**.

| Nhóm | Số ô | Kết quả |
|---|---|---|
| Quét thanh khoản: Setup A/B × 2 chiều × bộ lọc bật-tắt, 427 mã 4H | 8 | **loại cả 8** — 5 ô có KTC loại 0 về phía **lỗ** |
| **Cộng thêm** | **8 ô** | |

Tổng cắt ngang lên **58 ô**, ngưỡng Šidák **p < 0,000884**. Ở mức đó một lợi
thế thật +40 bps/lệnh vẫn trượt — nếu còn thử biến thể nữa thì phải tách mẫu
giữ lại, không cộng tiếp vào đây.

### Thêm ngày 27/10/2026 — frog-in-the-pan và động lượng phần dư

| Nhóm | Số ô | Kết quả |
|---|---|---|
| Frog-in-the-pan, chia dò < 2024-07 / kiểm ≥ 2024-07 | 1 | **loại** — trượt cả ba điều kiện |
| Động lượng phần dư, cùng cách chia | 1 | **loại** — trượt (1) và (2) |
| Bán khống perp mới niêm yết, chia theo ngày niêm yết | 1 | **loại** — trượt (1) và (2); mẫu sự kiện riêng |
| TVL Δ30 · perp/spot Σ30 · stablecoin Δ30, toàn mẫu | 3 | **loại** — Bonferroni 98,3%, perp/spot trượt (1) và (4) sát nút |

Tổng cắt ngang lên **156 ô** (gồm 1 ô xác nhận perp/spot bằng Bybit, 18 ô nhồi lệnh, 72 ô lệnh nhồi có khung + 1 ô xác nhận). Mỗi ô này được quyết bằng **nửa kiểm tách riêng**
đã tuyên bố trước, không bằng ngưỡng Šidák toàn mẫu.

Lưu ý: hai ô dùng **cùng một** nửa kiểm. Nửa đó giờ đã bị nhìn hai lần, nên
biến thể thứ ba trở đi không còn coi nó là sạch được nữa.

### Thêm ngày 28/10/2026 — stop ở đỉnh/đáy cũ và volume profile

| Nhóm | Số ô | Kết quả |
|---|---|---|
| Stop đỉnh/đáy cũ cho lệnh nhồi (12 cách × 2 đệm × 2 kiểu chốt) | 48 | **loại**. Tốt nhất +0,056R so với mốc ±1 ATR +0,085 |
| Stop đỉnh/đáy cũ cho lệnh gốc (12 × 2 đệm) | 24 | **loại**. ZigZag 3 cắt sụt ~23% mà không mất lãi, nhưng hơn gốc chỉ 3/6 năm |
| Volume profile cho lệnh nhồi (L × w × HVN/POC × đệm) | 24 | **loại**. R/lệnh −0,04 … +0,02 so với mốc +0,08 … +0,12 |
| Volume profile cho lệnh gốc | 24 | **loại**. POC 5 ngày cắt sụt gần một nửa nhưng lãi giảm 14%, hơn gốc 3/6 năm |
| **Cộng thêm** | **120 ô** | |

Tổng lên **276 ô**. Chi tiết ở `stop-dinh-day.md`. Các ô của RSI(2) trong cùng
đợt được tính bên `rsi2-connors.md`.

### Thêm ngày 28/10/2026 — tin huỷ niêm yết

| Nhóm | Số ô | Kết quả |
|---|---|---|
| Bán khống sau thông báo: 3 loại × k 3 × H 4 × stop 2 | 72 | **loại cả ba** — trượt KTC Bonferroni |
| Bán khống theo giờ đăng tin, nến 1 phút: 3 loại × trễ 4 × giữ 4 × stop 2 | 96 | **loại cả ba** — thẻ Monitoring sát nút (cận dưới −81 bps) |
| Bán khống trễ 1–60 giây, aggTrades: 3 loại × trễ 6 × giữ 4 × stop 2 | 144 | **thẻ Monitoring ĐẠT** (+650 bps, KTC [+29; +1.205]); gỡ spot / perp loại |
| Stop 1 / 2 / 3 / 5 / 10% cho các lệnh trên, xét từng giao dịch (theo yêu cầu, sau khi xem số) | 108 | stop càng chặt càng tệ — stop 1% chạm 79–93% số lệnh |
| Stop dời theo lời: 3 loại × trễ 2 × ngưỡng 3 × kiểu 3 × thảm hoạ 2 | 108 | **tin gỡ spot ĐẠT** (trễ 1 s, lời 15% thì dời stop về giá vào: +1.148 bps, tệ nhất −20,7% thay vì −129%) |

Tổng lên **804 ô**. Ba script nhìn vào **cùng một mẫu sự kiện**: tính chung
312 ô và gộp cụm theo bài thông báo thì cận dưới của thẻ Monitoring về −4 bps.
Đây là mẫu sự kiện riêng (mỗi sự kiện là một thông báo), không dùng chung nửa
kiểm với các ô cắt ngang.

## Điều này CHƯA chứng minh

1. **Chưa có kiểm định ngoài mẫu sạch.** Bộ tham số được chọn trên toàn mẫu;
   phép "bỏ 2026" là bằng chứng **củng cố**, không phải ngoài mẫu thật sự.
2. **Chưa đo trượt giá và tác động thị trường.** 2 mã mỗi chân trong top 20
   thanh khoản nên về nguyên tắc vào được cỡ lớn, nhưng chưa ai đo.
3. **Chưa tính chi phí vay / giới hạn bán khống.** Trên perp thì nhẹ hơn spot,
   nhưng funding đã tính còn hạn mức vị thế thì chưa.
4. **Chưa biết vì sao 2022 thua ở cả bảy sổ.** Có chuyện kể hợp lý (thị trường
   giảm đều, phân tán cắt ngang co lại) nhưng chưa đo.
5. **Chưa thử chân trời ngoài 30 và 90 ngày**, cũng chưa thử nhịp tái cân bằng
   ngoài 7 ngày.
6. **Lợi nhuận vẫn dồn theo thời gian.** Bỏ 10 kỳ tốt nhất trên 289 kỳ của một
   sổ: +34.677 bps → **−183**. Khác bản thô ở chỗ 10 kỳ đó trải trên nhiều năm,
   nhưng tính chất đuôi dày không đổi.
7. **Chìm 16,2 tháng là kịch bản phải chuẩn bị** (xem § "Thời gian âm khỏi
   đỉnh"): bản đã chốt có lọc MA30 cho đợt dài nhất **493 ngày**; bản không
   lọc là 586 ngày rơi + 75 ngày hồi = **661 ngày** dưới đỉnh cũ, và 94% số
   ngày của cả 5,5 năm nằm dưới đỉnh. Một sổ đơn lẻ có thể lên tới 898 ngày.

## Tệp

| Tệp | Việc |
|---|---|
| `scripts/screen_families.py` | Đợt sàng lọc 1: động cơ danh mục cắt ngang, carry, bám xu hướng, stat-arb. Bản đăng ký trước nằm trong docstring |
| `scripts/screen_more.py` | Đợt sàng lọc 2: 6 họ cắt ngang, p hai phía, Šidák toàn cục |
| `scripts/xsmom_ma_grid.py` | Lưới độ dài MA, luật quyết tuyên bố trước |
| `scripts/xsmom_rsi_filter.py` | Lọc RSI — đã thử, **bị loại** (mâu thuẫn cấu trúc) |
| `scripts/xsmom_ma_filter.py` | Bộ lọc MA30, hai cách diễn đạt + ghép cặp |
| `scripts/xsmom_risk_unit.py` | Đơn vị R + thử trọng số nghịch biến động |
| `scripts/xsmom_frog.py` | Frog-in-the-pan — đã thử, **bị loại**. Luật quyết trong docstring |
| `scripts/xsmom_resid.py` | Động lượng phần dư — đã thử, **bị loại**. Dùng lại `blend` của script ếch |
| `scripts/xsmom_detail.py` | Bóc từng năm, đường vốn đánh giá lại theo ngày |
| `scripts/xsmom_add.py` | Nhồi lệnh thuận / ngược — không thay |
| `scripts/add_bracket.py`, `add_bracket_confirm.py` | Lệnh nhồi có khung ±1 ATR: lưới rồi xác nhận 6 mốc cắt + phép giả |
| `scripts/swing_stops.py`, `vp_stops.py` | Stop ở đỉnh/đáy cũ và volume profile (chỗ A, B) — loại |
| `scripts/xsmom_page.py` | Dựng dữ liệu + trang UI |
| `scripts/webapp/static/xsmom.html` | Khuôn trang |
| `reports/xsmom.html` | Trang đã dựng (2,7 MB) |
