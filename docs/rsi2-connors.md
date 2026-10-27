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
lần). Mỗi lớp có stop, cỡ 1R và chỗ riêng (vẫn tính vào 5 chỗ); mọi lớp thoát
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
lớp    : tối đa 2 lớp mỗi mã — mua thêm khi tín hiệu lặp lại lúc đang giữ
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
| **Tổng** | **≈ 90** |

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
