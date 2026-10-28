# Tin huỷ niêm yết của Binance — gỡ spot + stop hoà vốn: ĐẠT · thẻ Monitoring: ĐẠT · gỡ perp: LOẠI · chặn mua: BẬT

**Ngày chạy:** 28/10/2026 · script `scripts/delist_short.py` (nến ngày) và
`scripts/delist_1m.py` (nến 1 phút), luật trong docstring, viết trước khi chạy ·
dữ liệu `scripts/delist_fetch.py`, `scripts/delist_1m_fetch.py` · 72 + 96 + 144 ô · thêm `scripts/delist_agg.py` (aggTrades)

Đây là phép thử đầu tiên về **đánh theo tin**. Chọn tin huỷ niêm yết vì ba lý
do: đây là tin xấu rõ ràng, có giờ đăng chính xác tới mili-giây, và giao dịch
được trên chính sàn ra tin.

## Dữ liệu

API thông báo công khai của Binance (`bapi/composite/v1/public/cms`), miễn phí:

| Mục | Số bài | Từ |
|---|---|---|
| «Delisting» (161) | 446 | 2022-02 |
| «Latest Binance News» (49) | 4.471 | 2017-07; giữ cả các thông báo gỡ mã trước 2022 |

Ba loại sự kiện. Mỗi cặp (loại, mã) chỉ lấy thông báo **đầu tiên**:

| Loại | Mẫu tiêu đề | Sự kiện | Có perp đang giao dịch | Khoảng |
|---|---|---|---|---|
| **S** gỡ khỏi spot | "Binance Will Delist X, Y on 2024-12-10" | 185 | 67 | 2023-03 → 2026-10 |
| **F** gỡ chính perp | "Binance Futures Will Delist XUSDT … Perpetual" (tiêu đề "Multiple …" thì đọc mã trong thân bài) | 97 | 84 | 2021-02 → 2026-10 |
| **M** gắn thẻ Monitoring | "Binance Will Extend the Monitoring Tag to Include X, Y" | 141 | 86 | 2023-10 → 2026-10 |

Bỏ qua: «Notice of Removal of … Trading Pairs» (chỉ gỡ cặp giao dịch, không gỡ
mã), gỡ khỏi margin / vay / staking / Alpha, quyền chọn, token đòn bẩy, đợt gỡ
hợp đồng BUSD năm 2023, và các thông báo hoãn gỡ.

## Phần lớn cú rơi xảy ra ngay trong ngày thông báo

Bot chạy theo nến ngày nên sớm nhất chỉ vào được ở open hôm sau.

| | Ngày thông báo, open → close (không vào kịp) | 4 ngày trước đó |
|---|---|---|
| S | TB **−19,4%** · trung vị −23,5% | −4,6% |
| F | TB −8,7% · trung vị −9,2% | −4,9% |
| M | TB −12,0% · trung vị −11,6% | −3,1% |

## Kiểm định: bán khống từ hôm sau

Cách vào lệnh:
- bán ở open ngày d + k (k = 1, 2, 3), giữ H ngày (1 / 3 / 7 / 14);
- stop: không có, hoặc giá vào + 3×ATR;
- phí 10 bps, tính funding thật;
- nếu perp bị gỡ giữa chừng thì đóng ở nến cuối còn khối lượng.

Mỗi loại 24 ô. Luật ra quyết định gồm 5 điều kiện:
1. KTC Bonferroni 72 ô loại 0;
2. ≥ 2/3 số năm dương;
3. bản rào BTC dương;
4. hơn p99 của phép giả (cùng mã, ngày ngẫu nhiên cách thông báo ≥ 60 ngày);
5. ≥ 2/3 ô lân cận dương.

| Loại | Ô chọn | n | TB bps | trung vị | KTC 99,93% | năm dương | phép giả p99 | Kết luận |
|---|---|---|---|---|---|---|---|---|
| **S** | k 3 · H 14 · stop 3 ATR | 67 | **+693** | +1.833 | [−1.022 ; +2.237] | 2/3 | +620 | **loại** ✗✓✓✓✓ |
| **F** | k 1 · H 14 · không stop | 79 | +613 | +749 | [−2.487 ; +2.122] | 2/4 | +983 | **loại** ✗✗✓✗✓ |
| **M** | k 3 · H 7 · stop 3 ATR | 86 | +292 | +468 | [−232 ; +930] | 2/3 | +430 | **loại** ✗✓✓✗✓ |

**S là loại gần đạt nhất.** Với stop 3 ATR, 10/12 ô cho TB dương; cả 8 ô vào
từ ngày thứ 2–3 đều dương (+81 … +1.069 bps), và kết quả vượt p99 của phép giả. Nhưng nó trượt điều kiện
(1), vì đuôi lỗ rất dày:
- **7/67 lệnh lỗ hơn 50%**: BOND −70%, BAKE −61%, NFP −59%, DENT −59%. Đó là
  những cú ép bán khống: mã sắp bị gỡ, nhiều người bán khống, funding âm
  (TB −0,9%/lệnh, bên bán phải trả), rồi giá bật mạnh.
- **Mẫu dồn vào hai năm gần đây**: 54/67 sự kiện thuộc 2025–2026; năm 2024 âm
  (−124 bps, 12 sự kiện).

**F có đuôi tệ nhất.** PUMPBTC tăng 365% sau thông báo gỡ perp, YALA tăng 131%.
Giá các perp này không còn neo vào spot.

Tóm lại: **có tín hiệu** (giá tiếp tục trôi xuống vài ngày sau thông báo),
**nhưng chưa phải chiến lược**. Mẫu nhỏ, đuôi ép bán khống quá dày, và phần lời
lớn nhất đã nằm trong ngày thông báo, lúc bot chưa vào kịp. Muốn lấy phần đó
thì phải đọc tin theo thời gian thực (WebSocket thông báo của Binance) và vào
lệnh trong vài giây — đó là một hệ thống khác hẳn.

## Đọc tin gần thời gian thực — nến 1 phút, cũng LOẠI

Script `scripts/delist_1m.py` (luật trong docstring), dữ liệu
`scripts/delist_1m_fetch.py` (nến 1 phút từ data.binance.vision, có cả mã đã bị
gỡ). Cùng các sự kiện như trên, nhưng vào lệnh theo giờ đăng bài thay vì chờ
nến ngày. Mỗi loại 32 ô:
- vào ở open của phút đầy đủ đầu tiên sau tin, trễ thêm L = 0 / 1 / 5 / 15 phút
  (L = 0 nghĩa là trễ 0–60 giây);
- giữ H = 15 phút / 1 giờ / 4 giờ / 24 giờ; stop không có hoặc +10%;
- chi phí 40 bps (10 phí + 30 trượt giá); điều kiện (5) kiểm lại ở 100 bps;
- chưa tính funding.

Quanh giờ đăng tin (bps, giá perp):

| Loại | 60 phút trước tin (TB / trung vị) | **phút đầu sau tin** | 24 giờ sau đó | khối lượng 5 phút đầu (trung vị) |
|---|---|---|---|---|
| S | −25 / −7 | **−1.055 / −1.117** | −724 / −1.315 | 2,0 triệu USD |
| F | −49 / +7 | +86 / −17 | −640 / −645 | 0,9 triệu USD |
| M | −31 / −15 | **−519 / −382** | −611 / −577 | 0,7 triệu USD |

Ba điều đọc được:
- **Không có rò rỉ trước tin.** 60 phút trước giờ đăng, giá gần như đứng yên,
  nên giờ đăng của API khớp với lúc thị trường biết tin.
- **Hơn một nửa cú rơi của tin gỡ spot xảy ra trong phút đầu** (−11%). Bot vào
  ở phút kế tiếp, tức trễ 0–60 giây, đã lỡ phần này. Phần đó thuộc về các bot
  phản ứng trong vài giây.
- **Phần trôi tiếp theo vẫn còn**: bán khống giữ 24 giờ được +400 … +700
  bps/lệnh sau chi phí. Nhưng đuôi lỗ vẫn dày, như ở nến ngày.

| Loại | Ô chọn | n | TB | KTC 99,95% | năm dương | phép giả p99 | @100 bps | Kết luận |
|---|---|---|---|---|---|---|---|---|
| S | L 1 · H 24 giờ | 67 | +682 | [−1.725 ; +1.813] | 3/3 | +80 | +622 | **loại** ✗✓✓✓✓ — lệnh tệ nhất −165% |
| F | L 0 · H 24 giờ · stop 10% | 84 | +416 | [−492 ; +1.370] | 2/4 | +116 | +356 | **loại** ✗✗✓✓✓ |
| M | L 0 · H 24 giờ | 86 | +571 | **[−81 ; +1.283]** | 3/3 | +81 | +511 | **loại, sát nút** ✗✓✓✓✓ |

**Thẻ Monitoring (M) là loại gần đạt nhất ở cả hai phép thử**: trượt đúng
điều kiện (1), cận dưới −81 bps. Đuôi của nó nhẹ hơn hẳn tin gỡ spot (lệnh
tệ nhất −32%), vì mã gắn thẻ chưa bị gỡ nên ít người bán khống và ít bị ép.

Kết luận: đọc tin gần thời gian thực thì **không khó** (Binance có WebSocket
thông báo). Nhưng ở độ trễ 1 phút, phần lời lớn nhất đã mất. Phần còn lại có
thật nhưng chưa vượt được luật Bonferroni với mẫu ~70–90 sự kiện. Câu hỏi còn
mở là trễ vài giây thì lấy được bao nhiêu trong phút đầu. Muốn trả lời cần dữ
liệu từng giao dịch (aggTrades), nến 1 phút không đủ.

## Trễ vài giây — aggTrades: thẻ Monitoring ĐẠT luật

Script `scripts/delist_agg.py` (luật trong docstring, viết trước khi chạy), dữ
liệu `scripts/delist_agg_fetch.py`: từng giao dịch perp trong cửa sổ
[−10 phút; +30 phút] quanh giờ đăng tin, đủ cả 237 sự kiện. Cách vào lệnh:
- bán khống trễ Δ = 1 / 2 / 5 / 10 / 30 / 60 giây;
- giá khớp **thận trọng**: giá thấp nhất trong 2 giây kể từ lúc vào;
- thoát sau H phút, đọc trên nến 1 phút; stop không có hoặc +10%;
- chi phí 40 bps, kiểm lại ở 100 bps;
- 144 ô.

**Đồng hồ sự kiện** — trung vị giá so với giao dịch cuối trước giờ đăng (bps):

| Loại | −60 s | 0 | +1 s | +2 s | **+3 s** | +5 s | +10 s | +60 s | +300 s |
|---|---|---|---|---|---|---|---|---|---|
| S | 0 | 0 | 0 | 0 | **−172** | −847 | −885 | −1.083 | −1.305 |
| F | 0 | 0 | 0 | 0 | 0 | 0 | −1 | −62 | −251 |
| M | 0 | 0 | 0 | 0 | **−215** | −256 | −378 | −460 | −561 |

Giá đứng yên hoàn toàn tới giây thứ 2, rồi rơi từ giây thứ 3. Như vậy giờ đăng
trên API chính xác tới vài giây, và các bot nhanh nhất mất khoảng 3 giây để
phản ứng. Với tin gỡ spot, khi giá khớp thận trọng ở Δ = 2 giây thì 92% cú rơi
của phút đầu đã xảy ra. Khối lượng 10 giây đầu khoảng 0,5–0,7 triệu USD (S, M),
nên lệnh vài trăm USD không làm động giá.

| Loại | Ô chọn | n | TB | KTC 99,965% | năm dương | phép giả p99 | @100 bps | Kết luận |
|---|---|---|---|---|---|---|---|---|
| S | Δ 1 s · H 24 giờ | 67 | +1.147 | [−588 ; +2.155] | 3/3 | +91 | +1.087 | **loại** ✗✓✓✓✓ — lệnh tệ nhất −129% |
| F | Δ 10 s · H 24 giờ · stop 10% | 84 | +491 | [−329 ; +1.395] | 2/4 | +113 | +431 | **loại** ✗✗✓✓✓ |
| **M** | **Δ 5 s · H 24 giờ** | 86 | **+650** | **[+29 ; +1.205]** | 3/3 | +78 | +590 | **ĐẠT** ✓✓✓✓✓ |

### Thẻ Monitoring — đạt, nhưng đọc cho đúng

Các phép kiểm thêm sau khi đạt (nhìn sau, không đổi kết luận của luật):

```
funding 24 giờ của bên bán khống   TB −9 bps → lời sau funding +640 bps
KTC gộp cụm theo tháng (22 cụm)     Bonferroni 144 ô [+34 ; +1.201] · 312 ô (cả 3 script) [+17 ; +1.298]
KTC gộp cụm theo bài (25 bài)       Bonferroni 144 ô [+41 ; +1.189] · 312 ô [−4 ; +1.231]
bỏ 3 / 5 lệnh tốt nhất              +547 / +504 bps
lệnh tệ nhất                         −15,6%
```

1. **Lợi thế không nằm ở tốc độ.** Với M giữ 24 giờ, trễ 1 s cho +635, trễ 5 s
   +650, trễ 60 s +529; bản nến 1 phút (trễ ~30 s) +571. Phần lời là **giá trôi
   xuống trong 24 giờ** sau khi mã bị gắn thẻ, không phải cú rơi của vài giây
   đầu. Bản này đạt còn bản 1 phút thì trượt sát nút, khác nhau chủ yếu ở giá
   khớp và ô được chọn. Hệ quả: đọc tin mỗi 30–60 giây là đủ, không cần chạy
   đua tính bằng mili-giây.
2. **Mẫu độc lập chỉ có 25 bài thông báo** (86 mã). Các mã trong cùng một bài
   chung một thời điểm thị trường. Tính cả ba lần nhìn vào cùng mẫu sự kiện
   (312 ô) và gộp cụm theo bài thì cận dưới về **−4 bps**. Đây là ứng viên tốt
   nhất từ trước tới giờ ngoài hai chiến lược đang chạy, nhưng chưa phải bằng
   chứng chắc chắn.
3. **2026 yếu hơn** (+369 bps, 50 mã) so với 2025 (+1.235, 25 mã). Có thể thị
   trường đã bắt đầu đánh theo tin này.
4. Đuôi lỗ nhẹ hơn nhiều so với tin gỡ spot (tệ nhất −15,6% so với −129%):
   mã gắn thẻ chưa bị gỡ, nên ít người bán khống và ít bị ép giá.

**Đề xuất:** chạy **sổ giấy** cho thẻ Monitoring. Đọc mục 49 mỗi 30–60 giây;
khi có bài «Extend the Monitoring Tag to Include …», bán khống perp của từng mã
trong vòng vài giây, giữ 24 giờ, không stop, cỡ lệnh nhỏ. Thẻ được gắn khoảng
mỗi tháng một lần, mỗi lần 1–9 mã. Muốn có 25 bài ngoài mẫu sẽ mất khoảng 2
năm.

**Tin gỡ spot (S)** là chỗ duy nhất tốc độ quyết định kết quả: trễ 1 s cho
+1.147, trễ 2 s còn +828. Nhưng đuôi ép bán khống (−129%) làm nó trượt luật ở
cả ba độ phân giải.

### Stop chặt (1–5%) — không cứu được, làm tệ hơn

Phép thử theo yêu cầu, **sau khi đã xem kết quả** (không đăng ký trước; cộng
vào kế toán). Script `scripts/delist_stop.py`. Stop được xét theo **từng giao
dịch**, với hai cách khớp:
- lạc quan: khớp đúng giá stop;
- thận trọng: giá cao nhất trong 1 giây sau khi chạm stop, giống lệnh
  stop-market khớp lúc giá đang vọt.

Tin gỡ spot, trễ 1 giây, giữ 24 giờ:

| Stop | chạm stop | TB lạc quan | TB thận trọng | thắng | lệnh tệ nhất |
|---|---|---|---|---|---|
| **1%** | **79%** | +409 | **+142** | 21% | −39% |
| 2% | 73% | +492 | +256 | 27% | −39% |
| 5% | 64% | +613 | +440 | 36% | −39% |
| 10% | 40% | +874 | +784 | 57% | −39% |
| không | — | **+1.147** | **+1.147** | 78% | −129% |

Ở trễ 5 giây, stop 1% chạm tới 93% số lệnh, và TB thận trọng âm (−89).

Lý do: **trong vài phút đầu sau tin, giá dao động ±5–10%**, giật xuống rồi bật
lại nhiều lần. Một stop 1% nằm gọn trong vùng nhiễu đó, nên 4/5 lệnh bị cắt
trước khi giá kịp trôi xuống. Đuôi lỗ không mất hẳn: giá có lúc nhảy 39% trong
một giây, nên lệnh stop-market khớp xa giá stop rất nhiều. Thẻ Monitoring và
tin gỡ perp cho kết quả cùng chiều: stop càng chặt thì TB càng thấp.

### Stop dời theo lời — tin gỡ spot ĐẠT, nếu vào trong ~1 giây

Script `scripts/delist_trail.py` (luật trong docstring, viết trước khi chạy).
Stop chỉ bật **sau khi** lệnh đã lời g = 5 / 10 / 15%:
- **BE**: dời stop về đúng giá vào (hoà vốn);
- **trail d**: stop = đáy thấp nhất × (1 + d), d = 10% hoặc 5%, chỉ hạ xuống;
- kèm stop thảm hoạ ban đầu: không có, hoặc +30%.

Vào trễ 1 / 5 giây, giữ 24 giờ, khớp stop thận trọng (giá cao nhất trong 1
giây sau khi chạm). 108 ô. Một loại đạt khi qua cả 5 điều kiện, trong đó
điều kiện (2) đòi giữ ≥ 80% lời của bản không stop **và** cải thiện cả lệnh
tệ nhất lẫn p5.

| Loại | Ô chọn | TB (không stop) | KTC 99,95% | p5 (không stop) | tệ nhất (không stop) | Kết luận |
|---|---|---|---|---|---|---|
| **S** | **Δ 1 s · g 15% · BE** | **+1.148** (+1.147) | **[+417 ; +1.913]** | −10,3% (−17,5%) | **−20,7%** (−129%) | **ĐẠT** ✓✓✓✓✓ |
| F | Δ 5 s · g 15% · BE | +755 (+517) | [−226 ; +1.565] | −11,0% (−32,1%) | −34,8% (−124%) | loại ✗✓✓✓✓ |
| M | Δ 5 s · g 15% · BE | +590 (+650) | [+38 ; +1.146] | −9,9% (−10,8%) | −15,6% (−15,6%) | loại ✓✗✓✓✓ — vốn không có đuôi để cắt |

**Vì sao nó chạy được với tin gỡ spot:** cú rơi đầu tiên rất nhanh và rất sâu.
79% số lệnh lời đủ 15% để kích hoạt stop trong vòng 24 giờ. Từ lúc
đó, một cú ép ngược kiểu ALPACA (đáy −21% sau 1 phút, rồi +175%) chỉ đưa lệnh
về **hoà vốn** chứ không còn lỗ −129%. Lời trung bình gần như không mất, vì
những lệnh tiếp tục trôi xuống không bao giờ quay lại chạm giá vào.

Các phép kiểm thêm cho ô S (nhìn sau, không đổi kết luận của luật):

```
funding 24 giờ (bên bán khống trả)   TB −94 bps → lời sau funding +1.055 … +1.088 bps
KTC gộp cụm theo tháng (23)           Bonferroni 108 ô [+207 ; +1.757] · 528 ô (cả 5 script) [+194 ; +1.807]
KTC gộp cụm theo bài (26)             Bonferroni 108 ô [+282 ; +1.773] · 528 ô [+177 ; +1.831]
ô lân cận Δ1s g15% trail 10%          +1.060 · 528 ô gộp theo bài [+316 ; +1.615]
ô lân cận Δ1s g10% trail 5%           +717  · 528 ô gộp theo bài [+265 ; +927]
cùng ô nhưng trễ 5 giây               +935  · 528 ô gộp theo bài [−316 ; +1.657] → KHÔNG đứng
```

Đây là kết quả đầu tiên đứng vững ngay cả khi tính chung mọi lần nhìn vào cùng
mẫu sự kiện và gộp cụm theo bài thông báo. Nhưng **nó chỉ đứng khi vào lệnh
trong khoảng 1 giây** (giá khớp là giá thấp nhất trong giây thứ 1–3). Trễ 5
giây thì khoảng tin cậy chứa 0. Với lại stop thảm hoạ +30% làm **tệ hơn**:
trong vài giây đầu có những cú giật lên rất mạnh, nên lệnh stop-market khớp ở
đỉnh giật.

**Điều chưa biết, phải đo trước khi dùng tiền thật:** bot nhận được tin sau
giờ đăng bao lâu. Giá thị trường bắt đầu rơi ở giây thứ 3, tức các bot nhanh
nhất nhận tin trong ~2 giây. Đọc API CMS mỗi giây sẽ bị chặn 429. Binance có
WebSocket thông báo (cần khoá API), nhưng độ trễ của nó chưa đo.

### Lỗi đã sửa trong lúc chạy

Lần chạy đầu, «mã còn sống» được lấy theo danh sách exchangeInfo. Nhưng perp
vừa bị gỡ vẫn nằm trong danh sách đó (trạng thái SETTLING), nên các lệnh có
perp chết giữa kỳ giữ bị **bỏ đi** thay vì được tính. Ví dụ ô S, H 7 chỉ còn
23/67 sự kiện. Đã sửa: mã còn sống khi nến cuối nằm trong 3 ngày cuối của kho.
`listing_short.py` cũng dính lỗi này. Chạy lại thì chỉ hai ô H 90 đổi vài sự
kiện, kết luận giữ nguyên.

## Chặn mua mã có tin huỷ niêm yết — đã cài vào bot

Hai chiến lược đang chạy đều có thể mua trúng mã đã có thông báo gỡ: động
lượng mua mã vừa bật mạnh, RSI(2) mua mã vừa rơi mạnh. Kết quả trên cho thấy
giá còn trôi xuống sau thông báo, nên mua vào lúc đó là đi ngược tin. Luật:

```
mã <base>USDT có thông báo S hoặc F trong DELIST_BAN_DAYS ngày (mặc định 90)
  → RSI(2): không mở lệnh mới, kể cả lớp mua thêm; chỗ trống nhường tín hiệu kế tiếp
  → động lượng: không mở chân MUA (bỏ hẳn, giống lọc MA30); chân BÁN giữ nguyên
  → vị thế đang giữ KHÔNG bị đóng sớm
```

Ngưỡng 90 ngày được chọn rộng tay. Phần lớn perp chết trong 1–2 tuần sau
thông báo S (45/67 chết trong 7 ngày). Nhưng có mã chỉ bị gỡ khỏi spot mà perp
vẫn sống: REEF bị gỡ spot ngày 26/08/2024, perp vẫn chạy, và tháng 9 động lượng
đã mua REEF bảy lần.

Code ở `trading-bot/app/delist.py`, luật tách tiêu đề chép nguyên từ
`delist_fetch.py`. Khi khởi động lần đầu, bot đọc hết mục 161 (~23 trang); sau
đó mỗi lượt chạy đọc 2 trang mới nhất. Lỗi mạng không chặn lượt chạy, danh sách
cũ vẫn còn trong bảng `delist`.

Tab «Tính lịch sử», cấu hình đang chạy (500 USD, 1R = 2):

| `delist_ban_days` | vốn cuối | CAGR | sụt | lần mua bị chặn |
|---|---|---|---|---|
| 0 (tắt) | 2.098,8 | 29,50% | 20,13% | — |
| 30 | 2.098,8 | 29,50% | 20,13% | 1 lần động lượng |
| **90** | **2.101,5** | **29,53%** | **20,13%** | 31 lần động lượng (7 lệnh REEF), 0 lần RSI(2) |

**Tác động lên lịch sử gần như bằng 0**, vì vũ trụ top 10 / top 20 thanh khoản
hiếm khi chứa mã sắp bị gỡ. Đây là một **chốt an toàn**, không phải nguồn lời:
nó chặn một kịch bản hiếm nhưng đắt, khi mã trong top đột ngột bị gỡ. Lịch sử
thông báo chỉ có từ 2022-02, nên trước mốc đó luật không có tác dụng.

## Chưa làm

- **Thẻ Monitoring (M)** chưa được đưa vào luật chặn. Sau khi gắn thẻ, giá cũng
  trôi xuống (bán khống TB +292 bps), nên đây là ứng viên thêm vào nếu muốn
  chặn rộng hơn.
- **Đóng sớm vị thế đang giữ** khi tin ra: chưa đo.
- **Sổ giấy đã chạy từ 29/10/2026** (`trading-bot/app/news.py`, tab «Nhật ký»
  → «Sổ giấy theo tin»). Nó chỉ ghi, không đặt lệnh: đo độ trễ nhận tin của
  mọi thông báo, và ghi lệnh bán khống giả cho tin gỡ spot (lời 15% thì dời
  stop về hoà vốn) và thẻ Monitoring (giữ 24 giờ).
  - WebSocket thông báo cần một **khoá API riêng chỉ quyền đọc**
    (`NEWS_API_KEY`). Khoá giao dịch hiện tại bị từ chối với `-2015`. Khi chưa
    có khoá đó, sổ giấy chỉ đọc API CMS mỗi 30 giây: vẫn đủ cho thẻ Monitoring,
    nhưng quá chậm cho tin gỡ spot.
  - Từ máy chạy bot, một lượt gọi tới fapi mất 0,6–0,9 giây đi về. Riêng việc
    đọc giá bán sau khi nhận tin đã tốn khoảng 0,3 giây.

## Tệp

| Tệp | Việc |
|---|---|
| `scripts/delist_fetch.py` | tải thông báo mục 161 + 49 + thân bài "Multiple …"; luật tách tiêu đề |
| `scripts/delist_short.py` | kiểm định bán khống nến ngày, 72 ô, phép giả |
| `scripts/delist_1m_fetch.py` | nến 1 phút quanh tin + ngày giả (data.binance.vision) |
| `scripts/delist_1m.py` | kiểm định bán khống theo giờ đăng tin, 96 ô |
| `scripts/delist_agg_fetch.py` | aggTrades ±10/30 phút quanh tin (data.binance.vision) |
| `scripts/delist_agg.py` | kiểm định trễ 1–60 giây, 144 ô — thẻ Monitoring đạt |
| `scripts/delist_stop.py` | stop 1–10% xét từng giao dịch, 108 ô (theo yêu cầu, không đăng ký trước) |
| `scripts/delist_trail.py` | stop dời theo lời (hoà vốn / trail), 108 ô — tin gỡ spot đạt |
| `reports/.cache/announce/` | `161.json`, `49.json`, `bodies.json` |
| `trading-bot/app/delist.py` | luật chặn mua trong bot |
