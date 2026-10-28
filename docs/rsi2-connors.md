# RSI(2) Connors — phương pháp v3.1 (đã chốt)

**Ngày chốt v3:** 26/10/2026 (v2: 25/10/2026) · **v3.1 sửa số:** 27/10/2026 · **Dữ liệu:** nến 1D (UTC) của Binance USDⓈ-M
futures, **toàn bộ 900 mã USDT perp từng tồn tại** kể cả đã huỷ niêm yết,
2020-09 → 2026-10-25. Funding thật từ `/fapi/v1/fundingRate`. Phí 10 bps
khứ hồi mỗi lệnh.

v1 (xem lịch sử git) chạy trên 36 mã còn sống, không lọc thanh khoản, không
stop. v2 đổi ba thứ: **vũ trụ có kiểm chứng**, **bộ lọc thanh khoản**, và
**stop có trần**. **v3 không đụng vào tín hiệu** — nó đổi cách định cỡ lệnh
sang [đơn vị R](money-management-r.md), thêm hai trần bắt buộc, loại tài sản
neo giá khỏi vũ trụ, và **sửa ba bảng sai** do luật đếm chỗ cũ.

**v3.1 không đổi luật — nó sửa một lỗi đếm làm mọi con số v3 phóng đại.**

## Bot đang chạy gì — 28/10/2026

Tín hiệu vẫn đúng v3.1 (vào RSI(2) < 10 và close > MA20, thoát RSI(2) > 70).
Phần vận hành lệch khỏi bản đặc tả ở bốn chỗ, đều do người vận hành chọn:

| Chỗ | Đặc tả v3.1 | Bot | Mức bằng chứng |
|---|---|---|---|
| Cắt lỗ | 6×ATR, trần 40% | **HVN gần nhất dưới giá − 0,25×ATR** (volume profile 20 ngày nến 1H), không có HVN thì 6×ATR | đạt luật, nhưng phần lớn là cỡ lệnh to hơn; Sharpe tháng chênh KTC chứa 0 — [stop-dinh-day.md](stop-dinh-day.md) |
| Mua thêm | 1 lớp | **3 lớp** (`RSI2_LAYERS=3`; mặc định trong mã là 2) | yếu — 26 lệnh lớp 2, xem § Mua thêm |
| 1R | 1R chung | **1R × 8** (`ALLOC_RSI2=8`) | đo bằng engine app — [money-management-r.md](money-management-r.md) § Ghép hai chiến lược |
| Đặt lệnh | thị trường (10 bps) | **LIMIT GTX** (maker), hết vòng thì lệnh đóng ra thị trường | backtest vẫn tính 10 bps |

Đã thử và **giữ nguyên**: chốt lời theo R / ATR / HVN / POC / đỉnh cũ (22 ô,
không ô nào hơn thoát RSI > 70 — [stop-dinh-day.md](stop-dinh-day.md) § Điểm
chốt lời), stop ở đáy cũ (24 ô, không hơn), khung 4H / 1H (không qua luật), lưới
tham số nến D (giữ bộ cũ).

Tab «Tính lịch sử» với cấu hình đang chạy (500 USD, 1R = 2, 2021-04 →
2026-10, cả hai chiến lược):

| | vốn cuối | CAGR | sụt | lãi riêng RSI(2) | sụt riêng RSI(2) | R TB RSI(2) |
|---|---|---|---|---|---|---|
| stop 6×ATR | 1.716 | 24,9% | 23,9% | 211 USD | 49 USD | +0,073 |
| **stop HVN (đang chạy)** | **2.099** | **29,5%** | **20,1%** | **593 USD** | **84 USD** | **+0,206** |

Stop HVN có ở 74/183 tín hiệu; 109 tín hiệu còn lại dùng 6×ATR, trong đó 19
tín hiệu là do mã thiếu nến 1H. Có 8 lệnh bị thu nhỏ về trần 500 USD. Sụt
riêng của RSI(2) tăng 71%, đúng như dự kiến khi lệnh to hơn. Sụt cả danh mục
tính bằng USD gần như không đổi (219 so với 218 USD); tính theo % thì thấp hơn
chỉ vì lúc đó vốn đã lớn hơn.

---

## v3.1 — một mã, một lệnh (27/10/2026)

`rsi2_universe.trades()` xét từng ngày độc lập, nên hai ngày RSI(2) < 10
liên tiếp sinh **hai lệnh chồng lên cùng một mã** — mã đang có lệnh vẫn được
mở thêm. Bot thật không làm thế: `rsi2_signals()` loại mã đang giữ. Lỗi
được tìm ra khi tab «Tính lịch sử» của app (mô phỏng đúng cơ chế bot) cho
lãi RSI(2) thấp hơn nghiên cứu ~35%.

Ở top 10: **33/176 lệnh (19%) là lệnh chồng**. Sửa bằng
`rsi2_universe.one_per_symbol()`, gọi **sau** khi lọc hạng thanh khoản; đặt
`RSI2_OVERLAP=1` thì mọi script dựng lại đúng số cũ (đã kiểm khớp bảng top N
từng ô). Cùng một quy trình, cùng hạt giống bootstrap:

| top 10 | v3 (có chồng) | **v3.1** |
|---|---|---|
| lệnh / năm | 176 / 32 | **143 / 26** |
| bps TB · thắng | +301,5 · 73,9% | **+255,4 · 70,6%** |
| KTC95 bps (khối 30 ngày) | [+104 ; +460] | **[+68 ; +433]** |
| train / test | +308 / +267 | **+261 / +225** |
| vốn N=5 · sụt | 2,64× · 18,9% | **2,02× · 16,7%** |
| CAGR/sụt | 1,03 | **0,82** |
| R TB · R tổng | +0,081 · +13,9 | **+0,072 · +10,3** |
| năm 2022 | +2,1% (phẳng) | **−3,1% (lỗ)** |

**Điều còn đứng:** KTC95 vẫn loại 0, train/test vẫn ổn định, lợi thế mỗi lệnh
vẫn cỡ +250 bps. **Điều đổi:** chiến lược yếu hơn ~15% mỗi lệnh, có một năm
lỗ, và lý lẽ "top 10 thắng CAGR/sụt" không còn — xem § Vì sao top 10.

Các mục **đã dựng lại** theo v3.1: Bộ tham số, Kết quả từng năm, bảng top N.
Các mục **còn mang số v3** (có chồng, chưa dựng lại): Hai cách diễn đạt khác,
Thiên lệch sống sót, Một cơ chế giải thích, Những gì đã thử, và số +137,5R
toàn vũ trụ. Chiều của các kết luận ở đó không đổi theo phép thử nhanh, nhưng
độ lớn thì có.

Script: `scripts/rsi2_v31.py` dựng mọi bảng v3.1 trong tài liệu này (chạy với
`RSI2_OVERLAP=1` ra lại bảng v3). `rsi2_topn_recheck.py`, `rsi2_risk_unit.py`
và `fixed_r_usd.py` cũng đã gọi `one_per_symbol`.

## Mua thêm — bật trong bot 27/10/2026 (lựa chọn vận hành)

Luật thêm: đang giữ một mã mà RSI(2) **lại** < 10 và close > MA20 thì mở
thêm một lớp, tối đa `rsi2.layers` lớp mỗi mã (**mặc định 2** — mua thêm một
lần; bot hiện đặt **3** qua `RSI2_LAYERS`). Mỗi lớp có stop, cỡ 1R và chỗ riêng (vẫn tính vào 5 chỗ); mọi lớp thoát
khi RSI(2) > 70.

Đây chính là phần v3 đã vô tình đo, nay làm có chủ ý. Lợi suất theo lớp, top
10, khi không giới hạn lớp:

```
lớp 1   143 lệnh   +255 bps   thắng 71%
lớp 2    26 lệnh   +399 bps   thắng 85%
lớp 3     5 lệnh   +848 bps   thắng 100%
lớp 4     2 lệnh   +963 bps   thắng 100%
```

Đo bằng engine của app (mô phỏng đúng cơ chế bot), RSI(2) riêng, 1R = 100:

| `rsi2.layers` | lệnh (mua thêm) | lãi USD | thắng | R TB | sụt USD | 2022 |
|---|---|---|---|---|---|---|
| 1 | 156 (0) | 946 | 69% | +0,061 | 243 | −93 |
| **2** | 179 (25) | **1.249** | 72% | +0,070 | **297** | **−22** |
| 3 | 183 (30) | 1.340 | 73% | +0,073 | 297 | −22 |
| 5 | 184 (31) | 1.367 | 73% | +0,074 | 297 | −22 |

Cấu hình thật (500 USD, 1R = 2, RSI(2) × 8): vốn cuối **1.653 → 1.702 USD**,
CAGR 24,0% → 24,7%, sụt 24,6% → 24,0%.

**Mức bằng chứng — ghi rõ để sau này không hiểu nhầm.** Đây là **lựa chọn
vận hành**, không phải kết luận thống kê: 26 lệnh lớp 2, nhìn thấy **sau**
khi đã xem số, chưa có quan sát ngoài mẫu nào. Cái giá có thật: sụt của
riêng RSI(2) tăng 22% (243 → 297), và mỗi lớp là thêm 1R vào **đúng mã đang
giảm mạnh nhất** — một token sập thật sẽ lỗ gấp đôi. Chọn 2 lớp chứ không 4
vì lớp 3–4 chỉ có 7 lệnh mà rủi ro tập trung nhân lên. Đặt `rsi2.layers = 1`
trong tab Cấu hình để tắt.

## Bộ tham số

```
vũ trụ : top 10 mã theo trung vị giá trị giao dịch USD 30 ngày,
         xếp hạng lại MỖI NGÀY, chỉ tính perp crypto
vào    : RSI(2) < 10  VÀ  close > MA20   → khớp ở open nến 1D kế tiếp
thoát  : nến đầu tiên có RSI(2) > 70     → khớp ở close nến đó
stop   : max(giá_vào − 6×ATR(14),  giá_vào × 0,60)
         (bot: HVN − 0,25×ATR khi có HVN dưới giá — xem § Bot đang chạy gì)
lớp    : tối đa 2 lớp mỗi mã — mua thêm khi tín hiệu lặp lại lúc đang giữ
         (bot: 3)
phí    : 10 bps/lệnh khứ hồi + funding thực tế
cỡ lệnh: risk% × vốn ÷ R,  R = (giá_vào − stop) / giá_vào
         trần cỡ một lệnh 25% vốn · tổng rủi ro đang mở ≤ 5 × risk%
loại trừ: perp của tài sản neo giá (USDCUSDT…) — xem § Hai điều khoản mới
```

Chỉ long. RSI(2) theo Connors, MA là SMA, mỗi mã cần **205 nến lịch sử** trước
khi được vào lệnh. **Lưu ý ATR:** repo này tính ATR = SMA của True Range,
không phải RMA của Wilder.

**143 lệnh (143 nhận được chỗ) · 26 lệnh/năm · bps TB +255,4 · thắng 70,6%**
**cắt lỗ 0,0% · KTC95 bootstrap khối 30 ngày: [+68 ; +433]**
**R trung bình +0,072 · R tổng +10,3** *(v3 có chồng: 176 lệnh · +301,5 · +0,081)*

Vặn mức rủi ro thì lợi nhuận và sụt đi lên cùng nhịp — tỷ lệ gần như bất
biến, nên **risk% là lựa chọn của người vận hành, không phải tham số khớp
dữ liệu**:

| risk%/lệnh | Vốn (5,5 năm) | Sụt tối đa | CAGR/sụt | *v3 (có chồng)* |
|---|---|---|---|---|
| 1% | 1,11× | 2,2% | 0,86 | *1,15× · 2,6%* |
| 3% | 1,35× | 6,6% | 0,87 | *1,50× · 7,7%* |
| 5% | 1,64× | 10,8% | 0,87 | *1,94× · 12,7%* |
| **7%** | **1,94×** | **15,0%** | **0,85** | *2,46× · 17,8%* |
| 10% | 2,35× | 21,1% | 0,80 | *3,24× · 25,3%* |

Mức **7%** cho sụt gần mức của cách chia 1/N (15,0% so với 16,7%), dùng làm
mốc đối chiếu. Ở 10% tỷ lệ bắt đầu tụt — đó là trần đòn bẩy.

**Chia đều 1/5 vốn mỗi lệnh để đối chiếu: 2,02× · sụt 16,7%** (v3: 2,64× ·
18,9%; con số 2,76× / 14,1% của v2 thì sai từ trước — xem § Ba bảng đã sửa).

## Kết quả từng năm

Đánh giá lại **theo ngày**, luật đếm chỗ đã sửa. Cột «vốn năm» đo trên đường
vốn nên lãi/lỗ rơi vào đúng ngày phát sinh, không dồn hết vào ngày đóng lệnh.

| Năm | Lệnh nhận | bps TB | Thắng | Vốn năm | Sụt trong năm | Luỹ kế |
|---|---|---|---|---|---|---|
| 2021 | 21 | +407,9 | 61,9% | 1,164× | 14,5% | 1,16× |
| 2022 | 26 | **−76,0** | 61,5% | **0,969×** | **16,7%** | 1,13× |
| 2023 | 20 | +201,7 | 70,0% | 1,065× | 6,9% | 1,20× |
| 2024 | 32 | +282,5 | 71,9% | 1,208× | 9,9% | 1,45× |
| 2025 | 20 | +557,8 | 85,0% | 1,242× | 9,5% | 1,80× |
| 2026¹ | 24 | +237,8 | 75,0% | 1,120× | 3,8% | **2,02×** |

¹ Dữ liệu chạy từ 2021-04 tới tháng 10/2026, tức **5,53 năm** chạm vào sáu
năm lịch — 2021 và 2026 đều là năm cụt.

**2022 là năm lỗ: −76 bps mỗi lệnh, vốn năm −3,1%.** Bản v3 ghi "không năm
nào âm, 2022 chỉ đứng yên" — câu đó dựa trên lệnh chồng và **sai**. Chiến
lược không sống qua mùa gấu bằng cách đứng ngoài hoàn toàn; nó vẫn mua các
nhịp quá bán trong xu hướng giảm và thua.

Sáu quan sát năm, hai cái cụt, trên mẫu 5,53 năm **chưa có kiểm định ngoài
mẫu sạch**. **Mỗi năm đều có một đợt sụt hai chữ số hoặc gần thế**, sâu nhất
là 16,7%.

**Stop không bắn phát nào trong cả sáu năm.** Giờ đã biết lý do: **79% số lệnh
(2.323/2.936 trên toàn vũ trụ) có stop nằm đúng ở trần 40%**, nghĩa là với đa
số lệnh thì `6×ATR` đã vượt trần. Trên thực tế chiến lược đang chạy với một
**stop thảm hoạ −40%**, không phải stop kỹ thuật. Điều đó đáng biết độc lập
với chuyện định cỡ.

37 mã khác nhau trong 5,5 năm, **12–15 mã mỗi năm** — danh sách tự xoay theo
thanh khoản chứ không cố định.

## Vì sao top 10 chứ không rộng hơn

Thanh khoản = trung vị giá trị giao dịch USD **30 ngày tính đến nến tín hiệu**,
xếp hạng chéo giữa mọi mã niêm yết ngày hôm đó. Hoàn toàn nhân quả.

Bảng v3.1 (một mã một lệnh). Bootstrap khối 30 ngày, hạt giống 101.

| top N | Lệnh | Nhận | bps TB | train | test | Vốn N=5 | Sụt | KTC95 |
|---|---|---|---|---|---|---|---|---|
| **10** | 143 | 143 | +255,4 | +261 | +225 | 2,02× | **16,7%** | **[+68, +433]** |
| 20 | 244 | 233 | +268,7 | +311 | **+52** | 2,78× | 25,7% | [+64, +480] |
| 30 | 338 | 301 | +217,5 | +227 | +174 | 3,03× | 28,4% | [+21, +385] |
| 40 | 434 | 345 | +234,7 | +230 | +257 | 2,67× | 39,9% | [+50, +407] |
| 50 | 543 | 403 | +179,1 | +209 | +35 | 2,29× | 36,5% | [+8, +353] |
| 75 | 763 | 492 | +148,8 | +186 | −26 | 2,69× | 41,0% | **[−42, +339]** |
| 100 | 983 | 568 | +178,1 | +202 | +74 | 4,22× | 37,7% | [−9, +344] |
| tất cả (498 mã) | 2.302 | 797 | +174,3 | +202 | +105 | **13,02×** | 51,6% | **[−6, +331]** |

Cột **«nhận»** là số lệnh thật sự tìm được chỗ. Với vũ trụ đầy đủ **65% số
lệnh bị bỏ** vì hết chỗ — số chỗ mới là thứ chặn trên, không phải số ứng viên.

| top N | Vốn | CAGR | Sụt | CAGR/sụt | *v3 (có chồng)* |
|---|---|---|---|---|---|
| **10** | 2,02× | ~13,7% | **16,7%** | 0,82 | *2,64× · 18,9% · 1,02* |
| 100 | 4,22× | ~29,8% | 37,7% | 0,79 | *5,40× · 40,9% · 0,87* |
| tất cả | **13,02×** | ~58,8% | 51,6% | **1,14** | *8,30× · 56,0% · 0,83* |

**Lý lẽ v3 cho top 10 không còn nguyên vẹn.** v3 nói top 10 thắng ở bps, ở
CAGR/sụt và là mức duy nhất có KTC loại 0. Sau khi bỏ lệnh chồng:

- **bps:** top 20 nhỉnh hơn (+268,7 so với +255,4) — không phân biệt được.
- **CAGR/sụt:** vũ trụ đầy đủ **cao hơn** (1,14 so với 0,82) — lệnh chồng
  từng đè lên nó nặng nhất, vì vũ trụ rộng có nhiều chuỗi quá bán nhiều ngày.
- **KTC loại 0:** top 10 đến top 50 đều loại 0; top 75 trở lên chạm 0.

Thứ **còn đứng**: top 10 có **sụt thấp nhất** (16,7% so với 25,7% của top 20
và 51,6% của toàn vũ trụ), **train/test ổn định nhất** (+261/+225, trong khi
top 20 rơi từ +311 xuống +52), và stop không bao giờ bắn. Giữ top 10 vì sụt
và độ ổn định — **không** vì CAGR/sụt.

Câu hỏi "có nên mở rộng vũ trụ không" giờ đáng hỏi lại, nhưng trả lời bằng
cách đổi tham số trên chính mẫu này là thêm một ô vào lưới tìm kiếm. Muốn hỏi
thì tách mẫu giữ lại hoặc dùng dữ liệu chạy thật.

Hai cách diễn đạt khác đều kém hơn:

| Cách | bps TB | KTC95 |
|---|---|---|
| top 10% (tương đối) | +261,3 | [+81, +428] |
| top 20% | +184,1 | [+19, +348] |
| ≥ 50M USD/ngày | +197,4 | [−5, +374] |
| ≥ 100M USD/ngày | +180,5 | [−20, +366] |

Lý do: **top-N tuyệt đối nghĩa là "nhóm vốn hoá đầu bảng"** bất kể sàn đã
niêm yết thêm bao nhiêu altcoin. Top 20% của 511 mã là 102 mã — không còn là
nhóm đầu bảng nữa.

## Thiên lệch sống sót — đã đo, không còn là rủi ro chính

Đây là rào cản số một của v1. Đã liệt kê toàn bộ 900 mã USDT perp từng tồn
tại (từ kho S3 của `data.binance.vision`, nơi giữ cả mã đã huỷ) và tải hết.

| | |
|---|---|
| Mã còn niêm yết | 659 |
| **Mã đã huỷ niêm yết** | **244** |
| Trong đó có ≥225 nến | **33** (225 mã còn lại là perp cổ phiếu niêm yết 2026) |
| Mã đã huỷ thực sự sinh ra lệnh | 19 · 73 lệnh |

| Tập | Lệnh | bps TB | KTC95 |
|---|---|---|---|
| Toàn vũ trụ 498 mã | 2.936 | +176,8 | [−2, +342] |
| Chỉ mã còn sống | 2.863 | +178,9 | [−7, +352] |
| Chỉ mã đã huỷ | 73 | +93,7 | [−323, +412] |

Mã đã huỷ kém hơn nhưng 73 lệnh thì không kết luận được gì.

**Kịch bản thảm hoạ — ôm lệnh khi token về 0 — gần như không xảy ra:** chỉ
**3/73 lệnh (4,1%)** kết thúc vì mã bị huỷ giữa lúc đang mở, tệ nhất −1.837
bps (MATICUSDT, mà MATIC là **đổi tên sang POL**, không phải chết).

**Lý do có cơ sở: điều kiện `close > MA20` loại token đang chết ngay từ cửa.**
LUNAUSDT là bằng chứng — Terra sập 09–13/05/2022, lệnh cuối cùng thoát ngày
**18/04**, ba tuần trước đó, tổng +449 bps. Suốt đường xuống giá nằm dưới
MA20 nên điều kiện vào lệnh không bao giờ đúng. Cùng cơ chế giải thích vì sao
MA20 lỗ −1.410 bps năm 2022 trong khi MA200 lỗ −32.943.

9/13 token thật sự chết lại có lãi. Ca duy nhất tệ là FRONTUSDT (−7.585 bps
trên 3 lệnh), và **trần 40% đã làm đúng việc**: lệnh tệ nhất dừng ở −4.039.

## Một cơ chế giải thích mọi hướng mở rộng thất bại

**Lợi thế tỉ lệ với biên độ con sóng thu hoạch được; phí thì cố định.**

| Hướng mở rộng | Kết quả | Lý do |
|---|---|---|
| Hạ khung 1D → 4H | +26 đến +33 bps, KTC chứa 0, train +48 / test **−43** | biên độ nhỏ đi ~10 lần, phí vẫn 10 bps → từ 30 lần phí còn 3 lần phí |
| Siết stop về khung nhỏ | đơn điệu xấu đi (xem dưới) | cắt mất phần dưới của chính con sóng đang chờ bật |
| Mở rộng danh mục | bps giảm, sụt vốn tăng gấp ba | thêm mã biên độ nhỏ, tương quan cao |
| Thêm MA thứ hai | p = 0,494 sau hiệu chỉnh | chỉ cắt bớt lệnh một cách trung tính |

**Stop ở khung nhỏ hơn một bậc (vào 1D, quản lý stop trên 4H)** — đơn điệu
hoàn hảo theo độ rộng stop:

| Cách đặt stop | Độ rộng | bps TB | Cắt lỗ |
|---|---|---|---|
| 6×ATR trên 1D (mốc) | 40,0% | **+310,6** | 1,8% |
| 10×ATR trên 4H | 32,7% | +293,5 | 3,2% |
| 6×ATR trên 4H | 19,6% | +273,3 | 12,4% |
| 3×ATR trên 4H | 9,8% | +251,4 | 28,0% |
| đáy 42 nến 4H | 3,1% | +88,8 | 62,6% |
| đáy 6 nến 4H | 1,9% | **+54,0** | **74,0%** |

Đặt stop dưới đáy swing 4H là thảm hoạ: đáy 6 nến chỉ cách giá vào 1,9%, nên
74% số lệnh bị cắt và tỷ lệ thắng rơi từ 75% xuống 26%. Vào 4H + stop 1H thì
mọi biến thể đều có KTC chứa 0 — không còn lợi thế nào để phá.

## Khung 4H đo lại bằng R, có lưới — 27/10/2026, LOẠI

Lần thử cũ dịch máy móc luật 1D sang 4H (RSI(2) = 8 tiếng, MA20 = 3,3 ngày)
và đo bằng bps/lệnh. Lần này đo bằng **R** (cỡ lệnh = 1R / khoảng stop, phí
tính trên danh nghĩa → phí_R = 10 bps / khoảng stop), quy đổi MA theo ngày,
lưới 36 ô: chu kỳ RSI 2/3/6 × vào 5/10/20 × ra 50/70 × MA 5/20 ngày. Top 10
thanh khoản, 5 chỗ, cùng engine chạy bản 1D làm mốc. Chưa tính funding (đã
kiểm riêng ở dưới: không đổi gì). Script `scripts/rsi2_4h_grid.py`.

| | lệnh | R/lệnh | R/năm | sụt R | R/năm÷sụt | stop TB | phí |
|---|---|---|---|---|---|---|---|
| **1D đang chạy** (cùng engine) | 156 | +0,062 | +1,7 | 2,0 | 0,86 | 35,5% | 0,003R |
| 4H ô chọn: RSI(2) < 5, ra > 50, MA 5 ngày | 401 | +0,036 | +2,6 | 1,8 | 1,43 | 19,4% | 0,007R |

Bằng R, câu chuyện "phí cố định ăn hết" **đúng một nửa**: stop 4H gần gấp
đôi nên phí ăn gấp đôi phần R (0,007 so với 0,003), nhưng nhiều lệnh hơn
bù lại — R/năm của ô chọn còn **cao hơn** 1D. Ô này qua cả bốn điều kiện
đăng ký trước (KTC Bonferroni 36 ô [+0,001 ; +0,069], dương 6/6 năm).

Nhưng ba cảnh báo, nên chạy thêm kiểm bền đăng ký trước
(`scripts/rsi2_4h_robust.py`):

- ô nằm ở **góc** lưới (ngưỡng vào thấp nhất, MA ngắn nhất), lân cận giảm
  dần 1,43 → 0,57 / 0,20 / −0,01 — dốc, không phải vùng ổn định;
- luật chọn ô **sửa sau lần chạy đầu** (ô < 30 lệnh bị gán −9 kéo điểm ô
  bên cạnh) — sửa đúng, nhưng vẫn là một bậc tự do;
- KTC chỉ vừa loại 0.

| Kiểm bền | Kết quả | |
|---|---|---|
| (A) mở rộng lưới quanh góc: vào 3/5/7 × ra 40/50/60 × MA 3/5/10 ngày | 27/27 ô dương, trung vị R/năm÷sụt 0,63; ô kề đạt 4/6 | **đạt** |
| (B) **dịch mốc giờ nến 4H** (dựng từ nến 1H) lệch 0 / 1 / 2 / 3 giờ | R/lệnh **+0,032 / +0,022 / −0,000 / +0,004** | **trượt** |
| (C) funding thật | +0,036 → +0,038R | đạt |

#### Bảng lưới đầy đủ

Mỗi ô: **R/năm ÷ sụt R** · R/lệnh · số lệnh. «—» = dưới 30 lệnh. Mốc 1D
cùng engine: 0,86 · +0,062 · 156.

Lưới 36 ô (vào / ra):

| RSI · MA | 5/50 | 5/70 | 10/50 | 10/70 | 20/50 | 20/70 |
|---|---|---|---|---|---|---|
| RSI(2) · 5 ngày | **1,43** · +0,036 · 401 | 0,57 · +0,032 · 398 | 0,20 · +0,010 · 1.272 | 0,09 · +0,006 · 1.238 | −0,13 · −0,006 · 3.083 | −0,13 · −0,011 · 2.741 |
| RSI(2) · 20 ngày | −0,01 · −0,001 · 1.109 | −0,03 · −0,003 · 1.051 | −0,12 · −0,008 · 2.184 | −0,11 · −0,010 · 1.937 | −0,17 · −0,014 · 3.848 | −0,15 · −0,019 · 3.132 |
| RSI(3) · 5 ngày | — (4) | — (4) | 0,14 · +0,018 · 94 | 0,12 · +0,019 · 94 | 0,08 · +0,007 · 938 | 0,03 · +0,004 · 904 |
| RSI(3) · 20 ngày | 0,13 · +0,020 · 153 | −0,05 · −0,014 · 152 | 0,02 · +0,002 · 651 | −0,08 · −0,013 · 612 | −0,10 · −0,009 · 1.902 | −0,10 · −0,015 · 1.540 |
| RSI(6) · 5 ngày | — (0) | — (0) | — (0) | — (0) | — (1) | — (1) |
| RSI(6) · 20 ngày | — (0) | — (0) | — (9) | — (9) | 0,13 · +0,017 · 284 | −0,05 · −0,012 · 272 |

11/24 ô đủ lệnh dương. Hai quy luật rõ: **MA 20 ngày giết lợi thế** (0/6 ô
dương ở RSI(2)), và **càng quá bán sâu càng tốt** (vào < 5 tốt hơn < 10, < 10 tốt hơn < 20).

Lưới mở rộng quanh góc, RSI(2) (vào / ra):

| MA | 3/40 | 3/50 | 3/60 | 5/40 | 5/50 | 5/60 | 7/40 | 7/50 | 7/60 |
|---|---|---|---|---|---|---|---|---|---|
| 3 ngày | — (22) | — (22) | — (22) | 4,84 · +0,057 · 104 | 1,18 · +0,046 · 104 | 1,06 · +0,045 · 104 | 0,88 · +0,029 · 273 | 0,63 · +0,028 · 273 | 0,52 · +0,030 · 273 |
| 5 ngày | 0,92 · +0,039 · 151 | 0,93 · +0,039 · 151 | 0,73 · +0,035 · 151 | 1,47 · +0,033 · 402 | **1,43** · +0,036 · 401 | 1,01 · +0,033 · 400 | 0,57 · +0,021 · 720 | 0,60 · +0,024 · 717 | 0,59 · +0,025 · 711 |
| 10 ngày | 0,28 · +0,009 · 373 | 0,10 · +0,005 · 371 | 0,00 · +0,000 · 371 | 0,54 · +0,014 · 812 | 0,38 · +0,012 · 804 | 0,14 · +0,007 · 798 | 0,47 · +0,013 · 1.258 | 0,35 · +0,012 · 1.231 | 0,14 · +0,006 · 1.204 |

Ngưỡng ra gần như không quan trọng; MA ngắn và quá bán sâu là tất cả.

Dịch mốc giờ của nến 4H, ô chọn:

| Nến 4H bắt đầu lúc | 0h | 1h | 2h | 3h |
|---|---|---|---|---|
| R/lệnh | +0,032 | +0,022 | −0,000 | +0,004 |
| R/năm ÷ sụt | 1,07 | 0,34 | −0,01 | 0,08 |

**(B) quyết định.** Chỉ cần nến 4H bắt đầu ở 02:00 thay vì 00:00 UTC là lợi
thế biến mất. Một hiệu ứng thật về hoảng loạn rồi bật lại không thể phụ
thuộc vào chỗ ta cắt nến; thứ phụ thuộc như vậy hoặc là may, hoặc gắn với
lịch của sàn (mốc funding 00/08/16 UTC trùng mốc nến 4H gốc) — giả thuyết
sau là một tín hiệu khác, chưa kiểm. Bài học trùng `dong-tien-cuong-buc.md`:
lưới thời gian cố định khiến mọi lệnh vào cùng một giờ, phải luôn dịch lưới.

### Cùng phép dịch mốc áp cho bản 1D ĐANG CHẠY — cũng phụ thuộc mốc

Dựng nến ngày từ nến 1H với mốc bắt đầu lệch 0–20 giờ, chạy đúng luật đã
chốt (RSI(2) < 10, ra > 70, MA20, stop 6×ATR, top 10, 5 chỗ), cùng engine R.
67 mã có đủ nến 1H; lệch 0 giờ tái tạo được bản gốc (+0,071 so với +0,062).

| Ngày bắt đầu lúc (UTC) | lệnh | R/lệnh | R/năm | R/năm÷sụt | 2022 |
|---|---|---|---|---|---|
| **00:00 (bot đang dùng)** | 121 | **+0,071** | +1,5 | 0,86 | −0,3 |
| 04:00 | 104 | +0,078 | +1,5 | 0,57 | −1,6 |
| 08:00 | 109 | +0,012 | +0,2 | 0,08 | −2,0 |
| 12:00 | 108 | +0,003 | +0,1 | 0,02 | −2,6 |
| 16:00 | 115 | −0,016 | −0,3 | −0,05 | −5,6 |
| 20:00 | 114 | +0,003 | +0,1 | 0,01 | −3,9 |

**Lợi thế của bản 1D chỉ có khi ngày được cắt ở 00:00–04:00 UTC.** Trung
bình 6 mốc chỉ +0,025R/lệnh, khoảng 1/3 con số đầu bảng. Hai cách đọc, dữ
liệu này chưa tách được:

1. **May** — mỗi mốc chỉ ~110 lệnh, KTC của bản gốc đã rộng [+0,014 ;
   +0,109]; con số đầu bảng là một lần rút thuận lợi.
2. **Neo vào nến chuẩn** — gần như cả thị trường nhìn nến ngày Binance cắt
   ở 00:00 UTC (mặc định của sàn và TradingView). "RSI(2) < 10 trên nến ngày"
   là tín hiệu đám đông *thấy*; trên nến lệch giờ thì không ai thấy nó. Mốc
   00:00 UTC cũng là ngay sau phiên Mỹ đóng cửa.

Cách 2 hợp lý về hành vi nhưng là giải thích **sau khi** thấy số. Nó cho
một dự đoán kiểm được: nếu đúng, lợi thế phải tập trung ở lệnh vào lúc
00:00 và các mốc lệch phải **tệ đều** chứ không ngẫu nhiên — bảng trên khớp
với điều đó (08–20 giờ đều ≈ 0), nhưng sáu điểm thì chưa đủ để gọi là
bằng chứng.

**Hệ quả vận hành:** bot dùng đúng nến 00:00 UTC nên nó đang giao dịch
đúng ô tốt. Nhưng hệ số `ALLOC_RSI2` = 8 được chọn theo con số đầu bảng; nếu
cách đọc 1 đúng thì lợi thế thật nhỏ hơn ~3 lần, và ×8 là quá tay. Chưa đổi
gì — ghi lại để theo dõi lệnh thật so với kỳ vọng +0,06R/lệnh.

**Trả lời "vì sao RSI không chạy dưới 1D":** không phải vì không có gì —
cả lưới quanh RSI(2) < 5 trên 4H đều dương nhẹ. Mà vì phần dương đó
**không bền với cách cắt nến** — và hoá ra bản 1D cũng vậy. Khác biệt duy
nhất: bản 1D chạy trên đúng cách cắt mà cả thị trường dùng.

## Nhồi lệnh (DCA / pyramiding) — 28/10/2026, KHÔNG THAY

Lệnh gốc giữ nguyên bộ đang chạy. Thêm lớp, quyết ở close, khớp open hôm sau,
**cùng stop** với lệnh gốc; mỗi lớp rủi ro 1R (đều) hoặc 1-2-4R (gấp đôi,
martingale) tới stop đó. Lưới 36 ô: chiều (ngược = giá giảm thêm d×ATR / thuận
= giá tăng thêm d×ATR) × d 1/2/3 × tối đa N 1/2/3 lớp × cỡ. Chấm trên 6 cách
cắt ngày. Script `scripts/rsi2_add.py`, luật trong docstring.

| | R/năm | sụt R | R/năm÷sụt | điểm 6 mốc | lệnh có nhồi | R của chúng |
|---|---|---|---|---|---|---|
| **gốc** | +1,74 | 2,02 | 0,86 | +0,25 | — | — |
| ngược d1 N2 đều | +3,72 | 3,35 | 1,11 | +0,30 | 41 | +0,4R tổng, thắng 56% |
| ngược d2 N1 đều | +2,39 | 2,08 | 1,15 | +0,34 | 18 | **−3,1R** tổng, thắng 39% |
| **ngược d3 N1 gấp đôi (ô chọn)** | **+3,08** | **1,86** | **1,66** | **+0,45** | **5** | +5,8R, thắng 5/5 |
| thuận (mọi ô) | +1,72 … +1,74 | 2,02 … 2,74 | 0,63 … 0,86 | ≤ +0,25 | gần 0 | — |

**Nhồi thuận không làm gì:** RSI(2) thoát ngay khi giá bật (RSI > 70), trước
khi giá kịp tăng thêm 2–3 ATR — ở d2/d3 không lệnh nào được nhồi. Cấu trúc
"bán khi mạnh" và "mua thêm khi mạnh" loại trừ nhau.

**Nhồi ngược ô chọn đẹp nhưng đứng trên 5 lệnh.** Cả cải thiện R/năm, 2022
từ −0,9 lên +2,4 lẫn sụt thấp hơn đến từ **5/156 lệnh** có nhồi — cả 5 đều hồi
lại. Chưa lệnh nào có nhồi chạm stop, nên lệnh tệ nhất vẫn ghi −1R, trong khi
rủi ro thật của mỗi lệnh nhồi là **3R** (1R gốc + 2R lớp gấp đôi). Nới ngưỡng
xuống 2 ATR để có 18 lệnh nhồi thì tổng của chúng **âm** (−3,1R); 1 ATR với 41
lệnh thì ≈ 0. Tức là không có hiệu ứng hệ thống "giá giảm thêm thì hồi mạnh
hơn" — chỉ có 5 lệnh may ở đuôi.

Theo luật: trượt (1) — chỉ hơn gốc 4/6 mốc cắt ngày. **Không thay.**

Liên quan: `rsi2.layers` của bot (mua thêm khi RSI(2) vẫn < 10 ngày hôm sau)
cũng là một dạng nhồi ngược theo thời gian, bằng chứng 26 lệnh lớp 2 — yếu
cùng kiểu.

## Quét lại 4H trên mọi mốc cắt, và lưới 1H — 27/10/2026

Lần trước chỉ ô 4H được chọn mới bị dịch mốc. Lần này **cả 62 ô 4H** chấm
trên 4 cách cắt nến (lệch 0/1/2/3 giờ, 73 mã), cộng **lưới 1H mới 54 ô**
(chu kỳ 2/3/6 × vào 5/10/20 × ra 50/70 × MA 3/5/20 ngày). Script
`scripts/rsi2_lowtf_scan.py`, luật trong docstring.

**4H — 11/47 ô đủ lệnh dương ở cả 4 mốc; 6 ô qua tiêu chí đặt trước**
(dương cả 4 mốc · điểm 4 mốc ≥ 0,25 = điểm 6 mốc của bộ 1D · ≥ 4/6 năm):

| RSI(2) vào / ra / MA ngày | R/lệnh 0h · 1h · 2h · 3h | R/năm TB 4 mốc | KTC95 R/tháng | KTC Bonf. 62 ô (mốc 0) | tương quan với 1D |
|---|---|---|---|---|---|
| 5 / 40 / 5 | +0,027 +0,013 +0,004 +0,006 | +0,65 | [−0,015 ; +0,122] | [−0,006 ; +0,058] | +0,17 |
| 5 / 50 / 3 | +0,054 +0,012 +0,012 +0,019 | +0,36 | [+0,003 ; +0,056] | [−0,010 ; +0,108] | +0,14 |
| 3 / 40 / 10 | +0,005 +0,020 +0,007 +0,009 | +0,57 | [−0,029 ; +0,116] | [−0,039 ; +0,039] | +0,10 |
| 5 / 40 / 10 | +0,010 +0,013 +0,005 +0,002 | +0,84 | [−0,061 ; +0,199] | [−0,026 ; +0,035] | +0,16 |
| 7 / 50 / 3 | +0,027 +0,013 +0,005 +0,011 | +0,51 | [−0,006 ; +0,091] | [−0,018 ; +0,073] | +0,10 |
| 7 / 40 / 3 | +0,027 +0,003 +0,006 +0,009 | +0,40 | [−0,009 ; +0,076] | [−0,016 ; +0,062] | +0,04 |

Một **vùng** có thật: quá bán sâu (< 3–7), MA rất ngắn (3–10 ngày), thoát
sớm (40–50). Bền với cách cắt nến — điều mà ô "tốt nhất" lần trước không có.
Nhưng nhỏ: 0,4–0,8 R/năm, và không ô nào có KTC Bonferroni loại 0. So sánh
công bằng: bộ 1D đang chạy, **trung bình 6 mốc cắt ngày**, cũng chỉ ~0,5
R/năm (+2,80R / 5,8 năm) — tức sau khi trừ phần "may của mốc 00:00", 4H và 1D
ngang nhau. Tương quan thấp (≤ 0,17) nên về nguyên tắc bổ sung được.

**Kết luận 4H:** có dấu hiệu, chưa có bằng chứng. Không đáng dựng bộ chạy
4H riêng (bot đang chạy theo ngày) cho 0,5 R/năm chưa chứng minh.

**1H — không có gì.** 10/44 ô đủ lệnh có R/lệnh > 0, không ô nào qua (KTC
Bonferroni 54 ô + ≥ 4/6 năm + R/năm÷sụt ≥ 0,86). Stop 1H chỉ cách ~8,7% nên
phí ăn **0,016R/lệnh** — gấp 5 lần 1D — trong khi lợi thế mỗi lệnh gần 0.
Không dịch mốc được cho 1H (kho chỉ có nến 1 phút của BTC).

## Lưới tham số trên nến D, chấm trên 6 mốc cắt ngày — 27/10/2026, GIỮ bộ cũ

Chu kỳ RSI và hai ngưỡng 10/70 là **mặc định Connors**, chưa từng quét trên
toàn vũ trụ. Lưới 81 ô: chu kỳ 2/3/4 × vào 5/10/15 × ra 50/70/80 × MA
10/20/50 ngày, đo bằng R, cùng engine với lưới 4H. **Mỗi ô chấm trên 6 cách
cắt ngày** (nến D dựng từ nến 1H, lệch 0/4/8/12/16/20 giờ, 67 mã) — điểm =
TB R/năm÷sụt qua 6 mốc. Script `scripts/rsi2_1d_grid.py`, luật trong docstring.

**57/81 ô không đủ lệnh — đúng cấu trúc, không phải lỗi:** RSI(2) < 10 là
hai ngày giảm mạnh liền nhau, nên giá gần như luôn **dưới** MA10 (BTC: 0 lệnh
cả 5,5 năm). Tương tự RSI(3)/(4) với MA20. Lưới có nghĩa thật chỉ có 24 ô.

Ô hợp lệ — điểm 6 mốc · [R/lệnh thấp nhất .. cao nhất qua 6 mốc]:

| | 10/50 | **10/70** | 10/80 | 15/50 | 15/70 | 15/80 |
|---|---|---|---|---|---|---|
| RSI(2) · MA20 | **+0,29** [+0,006 .. +0,059] | **+0,25** [−0,016 .. +0,078] ← đang chạy | +0,07 [−0,048 .. +0,080] | +0,14 [−0,008 .. +0,030] | +0,08 | +0,03 |
| RSI(2) · MA50 | +0,04 | +0,07 | +0,07 | +0,05 | +0,02 | +0,01 |
| RSI(3) · MA50 | +0,13 | +0,12 | +0,03 | +0,02 | +0,02 | −0,01 |

(Thêm: RSI(2)·MA50 vào < 5 cho +0,02 / +0,06 / +0,07; RSI(4)·MA50 vào < 15
cho +0,20 / +0,00 / −0,09.)

| | lệnh | R/lệnh gốc | KTC Bonferroni 81 ô | R/năm÷sụt gốc | 6 mốc R/lệnh |
|---|---|---|---|---|---|
| **Ô chọn: RSI(2) < 10, ra > 50, MA20** | 156 | +0,038 | [−0,025 ; +0,100] | 0,63 | +0,054 +0,059 +0,006 +0,017 +0,009 +0,029 |
| **Đang chạy: RSI(2) < 10, ra > 70, MA20** | 156 | +0,062 | [−0,027 ; +0,134] | 0,86 | +0,071 +0,078 +0,012 +0,003 **−0,016** +0,003 |

Ô chọn qua 4/5 điều kiện thay thế (dương 5/6 năm, dương **cả 6 mốc** — ô duy
nhất trong lưới làm được vậy, 3/3 lân cận, điểm 6 mốc cao hơn), trượt (1):
KTC Bonferroni 81 ô chứa 0. **Theo luật: giữ bộ đang chạy.**

Ba điều rút ra:

1. **Bộ đang chạy đứng thứ 2/24** theo điểm 6 mốc — Connors chọn mặc định
   gần như tốt nhất lưới. Không có bộ nào rõ ràng hơn.
2. **Thoát sớm (RSI > 50) bền hơn với cách cắt nến** nhưng lời ít hơn ở mốc
   00:00 mà bot dùng (+0,054 so với +0,071). Chọn giữa hai bộ chính là chọn
   giữa hai cách đọc ở mục trên: nếu thị trường neo vào nến 00:00 thì bộ
   đang chạy tốt hơn; nếu con số 00:00 là may thì ra > 50 an toàn hơn.
3. **Ở mức kế toán 81 ô, không ô nào — kể cả bộ đang chạy — có KTC loại 0.**
   Bằng chứng cho RSI(2) 1D đứng trên KTC95 của một ô duy nhất được chọn
   trước khi quét (+0,014 ; +0,109). Quét càng rộng thì ngưỡng càng cao; đây
   là cái giá của việc quét.

## Những gì đã thử và KHÔNG được

Mọi nỗ lực **chọn lệnh tại thời điểm vào** đều thất bại. Năm cách độc lập:

| Phép thử | Kết quả |
|---|---|
| **12 bộ lọc điểm vào** (rsi, atr, ma200, slope, drop1/3, ndown, vol, pos20, btcma, btcdd, breadth) | hoán vị khối max-over-12: **p = 0,45 (train) / 0,44 (test)** |
| **Gate breadth ≥ 15** | 406 lệnh nhưng chỉ **21 ngày**, gộp thành **8 đợt**; biến 2,65× thành 1,30×; p = 0,087 |
| **Xếp hàng tín hiệu cùng ngày** | đổi thứ tự lấy lệnh vô nghĩa làm kết quả nhảy 1,60× → 3,67× |
| **Ngắt sau khi cắt lỗ** | không sống sót đối chứng delta |
| **Đen-sổ mã theo thành tích** | tương quan train→test **−0,086**; 1/3 mã tệ nhất trên train lại là nhóm **tốt nhất** trên test |

Trần của việc này đã đo: khớp **cả 12 đặc trưng** vào kết quả, không giữ lại
tập kiểm tra, R² trong mẫu chỉ **4,15%** (nhãn xáo trộn cho 0,70%). **96%
biến động kết quả lệnh nằm ngoài tầm với của mọi thứ đo được lúc vào lệnh.**

**Bất đối xứng rút ra:** mọi thứ về **chọn lệnh lúc vào** đều thất bại; mọi
thứ về **xử lý sau khi vào** (độ rộng stop, luật thoát, độ dài MA lọc) và về
**chọn vũ trụ** (thanh khoản) đều có hiệu lực.

Đợt 28/10/2026 thử tiếp phía **xử lý sau khi vào**. Kết quả giữ đúng quy luật
trên ở phía stop, còn luật thoát thì đã gần tối ưu:

| Phép thử | Kết quả |
|---|---|
| **Stop ở đáy cũ** (pivot, Donchian, ZigZag, nổi bật; 24 ô) | không hơn 6×ATR. Đáy cũ gần nhất nằm trong vùng nhiễu nên cắt nhầm lệnh tốt |
| **Stop ở HVN của volume profile** (48 ô) | **đạt luật** (R/năm÷sụt 0,86 → 1,85, hơn 6/6 năm). Phần lớn cải thiện đến từ lệnh to hơn; Sharpe tháng 1,11 → 1,22, KTC chứa 0. Đã bật trong bot |
| **Chốt lời** R / ATR / HVN / POC / đỉnh cũ, có và không có thoát RSI (22 ô) | không hơn. Chốt xa trùng mốc vì RSI > 70 chạm trước; chốt gần cắt bớt lệnh thắng; bỏ thoát RSI làm sụt tăng 3–6 lần |

Chi tiết ở [stop-dinh-day.md](stop-dinh-day.md).

## Bẫy đã sập và cách gỡ

| Bẫy | Hậu quả nếu không gỡ |
|---|---|
| **Null không quy theo mức giá** | ATR 2021 đem sang mức giá 2025 làm mục tiêu không bao giờ chạm → null phình lên vài nghìn bps. Sập **hai lần**. Phải nhân span/barrier/ATR với `sc = px/base`. |
| **Max-over-variants thô** | Bị chi phối bởi biến thể phương sai lớn nhất → p = 0,71–0,88. Phải chuẩn hoá từng biến thể bằng null **của chính nó** rồi mới lấy max. |
| **Bootstrap theo từng lệnh** | Lệnh gần nhau chung chế độ → KTC hẹp giả. Phải bootstrap **khối 30 ngày**. |
| **Đối chứng xáo trộn sai** | Phải so **delta** với mốc không-luật trên **cùng** chuỗi. |
| **`stop >= px` không chặn `stop <= 0`** | ATR/giá tới 44,6% làm stop rơi xuống giá âm. |
| **Thanh khoản tính bằng trung vị TOÀN CHUỖI** | nhìn trước — năm 2021 không ai biết một mã sẽ thanh khoản thế nào đến 2026. Phải dùng trung vị **trượt 30 ngày**. |
| **REST trả nến rác cho mã đã huỷ** | sau ngày huỷ nó lặp giá cuối với **volume = 0** đến vô tận (SRMUSDT, COCOSUSDT). Phải cắt tại nến cuối có volume > 0. |
| **Ngưỡng downloader chặt hơn ngưỡng phân tích** | đặt 300 nến trong khi phân tích cần 225 → **48 mã bị vứt im lặng**, không báo lỗi. |
| **Perp cổ phiếu/kim loại chen vào bảng thanh khoản** | TSLA, AMZN, COIN, MSTR, XAU… không nằm trong `exchangeInfo` dạng USDT PERPETUAL nên không lọc được bằng `underlyingType`; chúng đẩy mã crypto khỏi top-20 và **thổi kết quả lên +343 bps**. Lọc bằng **tỷ lệ volume cuối tuần** (crypto 0,71–0,97; cổ phiếu ≤ 0,45) — phân tách tuyệt đối. |
| **Hạng thanh khoản khoá theo mốc NGÀY** | áp cho nến 4H thì chỉ nến 00:00 khớp → mất 5/6 tín hiệu. Phải làm tròn mốc về đầu ngày UTC. |

## Bội số phép thử — kế toán đầy đủ

| Nhóm | Số ô |
|---|---|
| Độ dài MA lọc xu hướng × độ rộng stop | 42 |
| MA thứ hai | 10 |
| Cách diễn đạt bộ lọc thanh khoản | 10 |
| Mức top N | 7 |
| Khung thời gian × cách đặt stop | 21 |
| Khung 4H bằng R: lưới 36 + lưới mở rộng 27 (27/10/2026) | 63 |
| Nến D: chu kỳ × ngưỡng vào × ngưỡng ra × MA, 6 mốc cắt (27/10/2026) | 81 |
| Nến 1H: lưới 54 ô (27/10/2026; 62 ô 4H chỉ chấm lại, không tính thêm) | 54 |
| Nhồi lệnh ngược / thuận (28/10/2026) | 36 |
| Stop ở đáy cũ: 12 cách × 2 đệm (28/10/2026) | 24 |
| Stop / chốt lời ở volume profile (28/10/2026) | 48 |
| Chốt lời với stop HVN: 11 mức × có/không thoát RSI (28/10/2026) | 22 |
| **Tổng** | **≈ 418** |

Đây là ô tốt trong khoảng 90 ô. Bằng chứng mạnh nhất chống lại lo ngại này:

- **top 10: train +308 / test +267** — không biến thể nào khác vừa cao vừa ổn
  định như vậy, và nó không được chọn vì lý do đó.
- **Ba cách đo độc lập hội tụ về ~+300 bps**: 36 mã của v1 (+293,1, chọn vì
  lý do hoàn toàn không liên quan — có sẵn nến 5m trong cache), top 10
  (+301,5), top 20 (+299,1). Hai tập mã chỉ trùng nhau một phần ba.

## Điều này chưa chứng minh

**1. Chưa có một quan sát nào thật sự ngoài mẫu.** Mọi tham số đều được chọn
sau khi nhìn toàn bộ 5,5 năm. Số lệnh từng ảnh hưởng đến quyết định mà không
nằm trong mẫu: **0**. Đây là rào cản cuối cùng trước tiền thật.

**2. Chưa có tiêu chí dừng ghi trước.** 2022 đi ngang trọn năm. Người thật sẽ
bỏ cuộc. Đề xuất: chạy nhỏ hoặc chạy giấy **6 tháng ở N=10**, kỳ vọng hợp lý
1,08–1,15×; dưới 1,0× hoặc sụt quá 12% thì dừng và xem lại.

**3. Trễ khớp lệnh bằng không.** Giá vào là giá tại đúng giây tín hiệu xuất
hiện. Đo trên nến 5m của tập 36 mã: chậm 5 phút mất ~5 bps, chậm 60 phút vẫn
giữ 93% kết quả. Chưa đo riêng cho tập top 10.

**4. Mẫu mỏng.** 176 lệnh, 32 lệnh/năm. Và vốn nằm không **77% số ngày** —
đây không phải chiến lược triển khai toàn thời gian.

**5. Chưa tính perp quote USDC.** Kho S3 có 1.056 mã, 900 kết thúc bằng
`USDT`. 156 mã còn lại (USDC/BUSD, coin-margined) bị bỏ qua có chủ ý: phần
lớn là bản trùng của cùng tài sản, thêm vào sẽ làm hỏng phép đếm thanh khoản.

**Đã gỡ ngày 27/10/2026 — trượt giá và độ sâu sổ lệnh.** Trước đó 10 bps là
hoa hồng thuần, không một bps nào dành cho spread. Đã đo trên 171 vị thế thật:
cỡ lệnh trung vị là **2,50× của 1R** (nhỏ vì 79% số lệnh có stop ở trần 40%),
tỷ lệ tham gia ở 1R = 100 USD là **0,00003%** khối lượng ngày, trượt giá chặn
trên **0,00 bps** (mốc 95%: 0,01 bps). Trần công suất vượt **1R = 100.000 USD**
ở cả hai tiêu chí. Phí 10 bps không bỏ sót gì — chi tiết và giới hạn của phép
suy rộng ở `docs/thanh-khoan.md`.

## Hai điều khoản mới của v3

**1 · Trần cỡ một lệnh 25% vốn.** Không phải đề phòng suông. Chạy toàn vũ trụ
không chặn gì, đỉnh đòn bẩy **9,78×** đến từ **một lệnh duy nhất**:

```
2026-05-10 · 8 vị thế mở
  USDCUSDT    stop cách  0,05%  →  cỡ 962,8% vốn
  7 lệnh khác stop cách 40,00%  →  cỡ   1,2% vốn mỗi lệnh
```

Thiếu trần này thì ở mức 3% rủi ro mỗi lệnh **tài khoản cháy** — vốn xuống âm.

**2 · Loại perp của tài sản neo giá.** `USDCUSDT` neo vào USD nên ATR gần 0,
và đảo chiều quá bán trên một đồng không có xu hướng là vô nghĩa. Trong kho
còn `BUSDT`, `TUSDT` cần kiểm. Bộ lọc `is_crypto()` theo khối lượng cuối tuần
**không bắt được** chúng vì chúng chạy 24/7 — cùng lỗ hổng đã để `MSTRUSDT`
(perp cổ phiếu MicroStrategy) lọt vào top 20 với tỷ lệ 0,53 so với ngưỡng
0,45.

## Ba bảng đã sửa trong v3

Bảng «từng năm», bảng «top N» và dòng tổng của v2 đều sinh ra từ một bản chạy
dùng luật đếm chỗ `z > t_`: vị thế thoát **đúng ngày** `t_` bị coi là đã nhả
chỗ, nên lệnh mới vào ở open cùng ngày trong khi lệnh cũ còn nắm tới close —
**chồng lấn**, tức âm thầm chạy quá 100% vốn. Luật đúng là `z >= ngày vào`.

Chạy lại luật cũ dựng đúng từng con số của bảng v2 (2,8× · 4,3× · 4,2× · 4,1×
· 5,3× · 8,1× · 19,0× · **504,5×**), khớp tám trên tám — nên nguyên nhân
không còn gì để tranh luận.

Sai số phình theo độ rộng vũ trụ: top 10 chỉ lệch 2,76 so với 2,64 vì hầu như
không ai chen vào khe một ngày đó; vũ trụ đầy đủ lệch **60 lần**.

Cột sụt của v2 còn chịu thêm một sai số thứ hai: đo lúc đóng lệnh thay vì
theo ngày, vốn đã biết là thấp hơn thực ~25%.

```
              2021    2022    2023    2024    2025    2026
v2 ghi         6,1%   14,1%    5,2%   12,2%    4,6%    1,8%
v3 tính lại   18,9%   16,7%    6,9%   14,8%    9,5%    5,2%
```

Ba script còn giữ luật cũ và **chưa được dùng lại**: `rsi2_best.py`,
`rsi2_ma20_stop.py`, `rsi2_trendma.py`.

## Tệp

| Tệp | Nội dung |
|---|---|
| `scripts/rsi2_v31.py` | **v3.1** — mọi bảng sau khi bỏ lệnh chồng; `RSI2_OVERLAP=1` ra lại v3 |
| `scripts/rsi2_risk_unit.py` | **v3** — định cỡ theo R, quét mức rủi ro |
| `scripts/rsi2_topn_recheck.py` | **v3** — dựng lại bảng top N, đối chiếu luật chỗ cũ |
| `scripts/rsi2_all_nocap.py` | **v3** — toàn vũ trụ không chặn vốn, hồ sơ đòn bẩy |
| `scripts/dvt_window.py` | **v3** — cửa sổ thanh khoản 30 so với 10 ngày |
| `scripts/rsi2_final.py` | **Luật v2** — ba cách diễn đạt bộ lọc thanh khoản, bảng từng năm |
| `scripts/rsi2_universe.py` | Toàn vũ trụ, thiên lệch sống sót, `is_crypto()` |
| `scripts/fetch_universe_1d.py` | Liệt kê + tải 900 mã USDT perp (resume được) |
| `scripts/fetch_universe_tf.py` | Tải nến 4H / 1H cho tập mã chỉ định |
| `scripts/rsi2_mtf.py` | Đa khung: vào 1D stop 4H, vào 4H stop 1H |
| `scripts/rsi2_4h_grid.py` | Khung 4H đo bằng R, có lưới; engine R dùng chung cho các script dưới |
| `scripts/rsi2_4h_robust.py` | 4H trên 6 mốc dịch giờ |
| `scripts/rsi2_1d_grid.py` | Lưới nến D chấm trên 6 mốc cắt ngày (`day_from_1h`) |
| `scripts/rsi2_lowtf_scan.py` | Quét 4H mọi mốc + lưới 1H |
| `scripts/rsi2_add.py` | Nhồi lệnh thuận / ngược |
| `scripts/swing_stops.py` | Stop ở đỉnh/đáy cũ, bốn cách xác định |
| `scripts/vp_stops.py` | Stop / chốt lời ở volume profile — nguồn của stop HVN trong bot |
| `scripts/rsi2_tp.py` | Điểm chốt lời với stop HVN |
| `scripts/rsi2_deploy.py` | Lưới trần stop (30/35/40%) |
| `scripts/rsi2_ma20_stop.py` | Lưới MA20 × 6 độ rộng stop |
| `scripts/rsi2_trendma.py` | Lưới 7 độ dài MA + null vào lệnh ngẫu nhiên |
| `scripts/rsi2_ma2.py` | MA thứ hai (10 biến thể) |
| `scripts/rsi2_live.py` | Hiệu ứng chọn trên 42 ô, khớp lệnh trễ, kịch bản mã về 0 |
| `scripts/rsi2_filter.py` | 12 bộ lọc điểm vào |
| `scripts/rsi2_breadth.py` | Gate breadth ≥ 15 |
| `scripts/rsi2_why.py` | 6 phép chẩn đoán nguyên nhân thua |
| `scripts/rsi2_best.py` | Bảng từng năm + trang UI (v1, chưa cập nhật sang v2) |
| `scripts/strategy_backtest.py` | 10 chiến lược gốc, khung 1D |
| `reports/.cache/uni1d/` | 900 mã klines 1D + 635 funding |
| `reports/.cache/uni_tf/` | 432 mã 4H · 82 mã 1H |

Chạy luật v2:

```
.venv/bin/python scripts/rsi2_final.py
```
