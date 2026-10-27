# Hướng thanh khoản

Chốt ngày 27/10/2026. Hai nghĩa của "thanh khoản", bốn câu hỏi.

| Câu hỏi | Kết quả | Mục |
|---|---|---|
| Ước được spread từ OHLC không? | **Không.** Hai ước lượng tiêu chuẩn đang đo độ biến động | §1 |
| Phí 10 bps có thiếu phần thanh khoản? | **Không.** Trượt giá ở 1R = 100 USD là 0,01 bps | §2 |
| Thanh khoản làm nhân tố cắt ngang được không? | **Không.** KTC chứa 0 ở cả bốn chiều | §3 |
| Quét thanh khoản (SFP) giao dịch được không? | **Tín hiệu thật, chiến lược không.** Setup B *lỗ* có ý nghĩa thống kê | §5 |

Giá trị của đợt này không nằm ở một chiến lược mới, mà ở hai chỗ. Một là **gỡ
một mối đe doạ**: trước đợt này không ai biết 10 bps có bỏ sót chi phí thanh
khoản hay không — giờ thì biết, và biết luôn trần vốn. Hai là **tách được dự
báo khỏi lợi nhuận** ở Setup A: cú quét đáy dự báo được +39 bps so với vào lệnh
ngẫu nhiên, nhưng lợi suất thô chỉ +3,0 bps nên phí 10 bps ăn hết.

---

## 1. Ước lượng spread từ OHLC — đã bác bỏ

Kho không có lịch sử bid/ask, nên hướng đầu tiên là ước spread từ chính nến
ngày bằng hai ước lượng tiêu chuẩn:

- **Abdi–Ranaldo (2017)** CHL: `η_t = (ln h_t + ln l_t)/2`,
  `S² = 4·E[(c_t − η_t)(c_t − η_{t+1})]`
- **Corwin–Schultz (2012)** hai nến cao-thấp

Cửa sổ 30 ngày, kết thúc ở chính nến tín hiệu (cặp cuối là `(i−1, i)`, không
dùng nến `i+1`) — không nhìn trước. 442.692 ô, 623 mã.

Kết quả vô lý ngay từ dòng đầu:

| hạng thanh khoản | A–R trung vị | A–R TB | C–S trung vị |
|---|---|---|---|
| 1–5 | 0,0 | 74,1 | **156,2** |
| 6–10 | 0,0 | 88,4 | 204,3 |
| 11–20 | 0,0 | 108,8 | 210,4 |
| 101+ | 0,0 | 98,7 | **199,1** |

Spread 156 bps cho nhóm 5 mã thanh khoản nhất sàn là không thể. Phép kiểm
quyết định:

```
tương quan C–S với biên độ cao-thấp 30 ngày : +0,860
tỷ lệ C–S / biên độ, trung vị               :  0,254
C–S ở top-20 : 197 bps      C–S ở hạng 101+ : 199 bps
```

**C–S bằng đúng một phần tư biên độ cao-thấp, ở mọi hạng thanh khoản.** Một
ước lượng không phân biệt được BTCUSDT với một mã microcap thì nó đang đo độ
biến động, không đo spread. A–R thì hơn một nửa số ô bị kẹp về 0 — ước lượng
`S²` ra âm, tức tín hiệu nằm dưới sàn nhiễu.

Lý do có thể nói trước, và lẽ ra nên nói trước: cả hai ước lượng được thiết kế
cho **nến ngày của chứng khoán**, nơi spread so với biên độ ngày lớn hơn
crypto perp vài bậc. Ở đây spread thật cỡ 0,1–2 bps còn biên độ cao-thấp ngày
là **805 bps** (trung vị top-20). Tỷ lệ tín hiệu trên nhiễu là 1:400. Không
ước lượng OHLC nào gỡ được chuyện đó.

**Không dùng tiếp hướng này.** Script giữ lại làm chứng cứ:
`scripts/liq_spread.py`.

---

## 2. Chi phí thanh khoản thật — không phải mối đe doạ

### Nguyên liệu: bookDepth THẬT

Thay vì ước, đo. Kho có `bookDepth` của Binance USDⓈ-M cho BTCUSDT:
**380.686 ô 5 phút**, 2023-01 → 2026-10, độ sâu tích luỹ theo USD ở các mốc
±1%…±5% quanh mid.

```
BTCUSDT · độ sâu phía ask trong 1% quanh mid (triệu USD)
  trung vị 129,0      mốc 5% 71,8      mốc 95% 314,7
giá trị giao dịch/ngày, trung vị : 13.248 triệu USD
→ tỷ lệ depth(1%) / khối lượng ngày = 0,0097
```

Ngay cả ở mốc 5% — tức những lúc sổ lệnh mỏng nhất trong gần 4 năm — vẫn có
**71,8 triệu USD** chờ trong phạm vi 1%.

> **Giới hạn phải nói rõ:** kho chỉ có bookDepth của **một** mã. Áp tỷ lệ
> 0,0097 cho các mã khác là một **phép suy rộng**, không phải đo trực tiếp.
> Nó giả định độ sâu tỷ lệ với khối lượng ngày. Với mã thanh khoản kém hơn
> BTCUSDT, tỷ lệ đó có thể thấp hơn.

Trượt giá tính theo **chặn trên bi quan có ý**: coi độ sâu phân bố *đều* trong
dải 1%, nên lệnh X USD đẩy giá `100 bps × X / depth(1%)`. Thực tế độ sâu dày
đặc gần mức giá tốt nhất, nên số thật nhỏ hơn. Đây là **trần**, không phải ước
trung tâm.

### Tỷ lệ tham gia của lệnh thật

Đo trực tiếp, không suy rộng gì: cỡ lệnh chia cho giá trị giao dịch ngày của
chính mã đó.

**Động lượng cắt ngang** — 6.601 vị thế:

```
cỡ lệnh / 1R         : trung vị 6,94×  ·  95% 16,94×  ·  99% 24,98×
KL ngày của mã vào lệnh : 5% 137 tr  ·  trung vị 433 tr  ·  95% 9.641 tr USD
```

Hệ số 6,94× là hệ quả trực tiếp của việc động lượng **không có cắt lỗ**: 1R
của nó là `σ(log 30n) × √7 ≈ 14%`, nên cỡ lệnh = 1R / 0,14 ≈ 7×R. Đối chiếu
chéo: 694 USD × 23 vị thế trung vị = ~16.000 USD, khớp với phơi nhiễm trung vị
**17.690 USD** đã đo ở đợt trước. Harness nhất quán.

| 1R (USD) | cỡ lệnh tv | tham gia tv | trượt tv | trượt 95% | trượt 99% |
|---|---|---|---|---|---|
| **100** | 694 | 0,00014% | **0,01** | **0,08** | 0,14 |
| 1.000 | 6.938 | 0,00144% | 0,15 | 0,76 | 1,43 |
| 10.000 | 69.378 | 0,01436% | 1,47 | **7,57** | 14,31 |
| 50.000 | 346.891 | 0,07180% | 7,37 | 37,86 | 71,53 |
| 100.000 | 693.781 | 0,14359% | 14,75 | 75,73 | 143,05 |

**RSI(2)** — 171 vị thế, cỡ lệnh / 1R trung vị **2,50×** (nhỏ hơn 2,8 lần vì
nó *có* cắt lỗ, và 79% số lệnh có stop nằm ở trần 40%):

| 1R (USD) | trượt tv | trượt 95% |
|---|---|---|
| **100** | 0,00 | **0,01** |
| 10.000 | 0,34 | 1,13 |
| 100.000 | 3,37 | 11,31 |

### Kết luận về chi phí

Ở cấu hình đang chạy (**1R = 100 USD**), trượt giá là **0,01 bps** cho động
lượng và **0,00 bps** cho RSI(2) — ba bậc độ lớn dưới 10 bps hoa hồng. Phí
10 bps **không** bỏ sót chi phí thanh khoản. Không phải sửa gì trong hai bản
đã chốt.

Chia theo hạng thanh khoản ở 1R = 100 USD, trượt giá ở mốc 95%:

| hạng | động lượng | RSI(2) |
|---|---|---|
| 1–5 | 0,018 bps | 0,005 bps |
| 6–10 | 0,049 bps | 0,016 bps |
| 11–20 | 0,098 bps | — |

Năm tệ nhất là 2026: mốc 95% lên 0,123 bps, mốc 99% lên 0,240 bps. Vẫn là số
không đáng kể.

### Trần công suất

Ngân sách trượt giá **tuyên bố trước khi nhìn kết quả**: 10% lợi thế gộp mỗi
lệnh — tức 14,3 bps cho động lượng (lợi thế +143,3 bps/kỳ) và 30,2 bps cho
RSI(2) (+301,5 bps/lệnh).

| chiến lược | theo trung vị | theo mốc 95% | phơi nhiễm đỉnh tương ứng |
|---|---|---|---|
| Động lượng | 1R ≤ 50.000 USD | **1R ≤ 10.000 USD** | ~4,5 triệu USD |
| RSI(2) | > 100.000 USD | > 100.000 USD | > 1,25 triệu USD |

Lấy mốc 95% làm chuẩn vì trung vị không bắt được lệnh tệ. Động lượng là chiến
lược bị chặn trước: **1R = 10.000 USD**, tức gấp **100 lần** cấu hình hiện
tại, ứng với phơi nhiễm đỉnh khoảng 4,5 triệu USD (quy từ đỉnh 44.796 USD đo
được ở 1R = 100).

Nói cách khác: thanh khoản **không phải** thứ chặn hệ thống này ở quy mô cá
nhân. Thứ chặn nó là vốn, và sau vốn là các giới hạn sàn (`minNotional`,
`stepSize`) ở đầu dưới — không phải độ sâu sổ lệnh ở đầu trên.

Script: `scripts/liq_capacity.py`.

---

## 3. Thanh khoản làm tín hiệu — không có lợi thế

Trong cả kho này thanh khoản chỉ từng được dùng làm **bộ lọc vũ trụ** (chọn
top-N rồi bỏ đi), chưa bao giờ làm **tín hiệu**. Đó là chỗ trống, nên thử.

### Đăng ký trước

**Ô A · Phi thanh khoản Amihud.** `ILLIQ[i]` = trung vị của
`|log(C_j/C_{j−1})| / giá_trị_gd_USD_j` trên 30 ngày tính đến nến `i`. Trung vị
chứ không trung bình: tỷ số này có đuôi cực béo. Mua decile **phi thanh khoản
nhất**, bán decile **thanh khoản nhất**. Lý thuyết: chứng khoán có *phần bù phi
thanh khoản* — tài sản khó vào được phải trả lãi suất cao hơn.

**Ô B · Sốc thanh khoản.** `SHK[i]` = giá trị gd ngày `i` chia trung vị 30 ngày
của chính nó. Mua decile bùng nhất, bán decile khô cạn nhất.

Hai phía, không dự đoán trước về dấu. Cố định hết, không quét: vũ trụ top-50,
cửa sổ 30 ngày, H = 7 ngày, decile 10%, đều vốn, 7 sổ lệch pha, phí 10 bps khứ
hồi, funding thực.

### Cảnh báo đã viết ra trước khi chạy, và nó đã xảy ra

ILLIQ gần như là nghịch đảo của chính giá trị giao dịch, tức của hạng thanh
khoản dùng để chọn vũ trụ. Ngưỡng tuyên bố trước: `|r| > 0,9` thì phải đọc nó
như một **nhân tố cỡ mã trá hình**.

```
tương quan hạng ILLIQ với hạng thanh khoản (trong top-50) : +0,829
```

Dưới ngưỡng, nhưng **chỉ vừa đủ**. 0,829 nghĩa là phần lớn những gì ô A đo là
cỡ mã, không phải thanh khoản. Đọc kết quả bên dưới với điều đó trong đầu.

### Kết quả

bps mỗi kỳ 7 ngày, ròng phí và funding. KTC **99,899%** (Šidák), bootstrap
khối 21 kỳ, 2.019 kỳ:

| ô | bps/kỳ | KTC đã hiệu chỉnh | vốn gộp | sụt | |
|---|---|---|---|---|---|
| A · Amihud — mua PHI thanh khoản | −42,9 | [−120,4 ; +52,9] | 0,21× | 85,5% | — |
| A' · Amihud — đảo dấu | +22,9 | [−72,9 ; +100,4] | 1,38× | 63,9% | — |
| B · Sốc KL — mua BÙNG | +10,8 | [−87,4 ; +97,3] | 0,86× | 66,7% | — |
| B' · Sốc KL — đảo dấu | −30,8 | [−117,3 ; +67,4] | 0,22× | 82,6% | — |

Dấu — : khoảng tin cậy **chứa 0** ⇒ không có lợi thế. Cả bốn chiều đều vậy.

Theo từng năm:

| năm | A | A' | B | B' |
|---|---|---|---|---|
| 2021 | 1,14× | 0,75× | 1,55× | 0,51× |
| 2022 | 1,09× | 0,80× | 0,88× | 0,91× |
| 2023 | 0,93× | 0,86× | 0,62× | 1,50× |
| 2024 | 0,73× | 1,08× | 1,43× | 0,54× |
| 2025 | 0,48× | 1,73× | 1,52× | 0,58× |
| 2026 | 0,57× | 1,31× | 0,47× | 1,04× |

Không ô nào có một hướng ổn định qua các năm.

### Hai điều đáng ghi lại

**Harness tự kiểm chứng.** A và A' phải là ảnh gương của nhau *trừ đi hai lần
phí*. Kiểm: trung bình của −42,9 và +22,9 đúng bằng **−10,0 bps** = phí khứ
hồi. Vậy lợi thế gộp của Amihud là ±32,9 bps/kỳ — so với **+143,3 bps/kỳ** của
động lượng đã chốt, tức yếu hơn 4,4 lần, và với KTC rộng gấp nhiều lần.

**Ô B là bản tái lập, không phải ô mới.** Sốc khối lượng đã nằm trong đợt sàng
lọc cũ (`xsmom-volnorm.md`, bảng «Những gì đã thử và KHÔNG được»): trượt Šidák
với p = 0,028, dấu *khối lượng cao thì tốt hơn*. Ô B ở đây ra **đúng dấu đó**
(+10,8 bps cho chiều mua-bùng) trên một vũ trụ và một định nghĩa khác. Tái lập
được là tốt, nhưng nó **không** được đếm thêm vào kế toán.

Script: `scripts/liq_factor.py`.

---

## 4. Kế toán đa phép thử

| | |
|---|---|
| Trước đợt này | 49 ô · p < 0,00105 |
| Ô A · Amihud (mới thật) | +1 |
| Ô B · sốc khối lượng | +0 — **tái lập** ô đã có |
| **Sau §1–§3** | **50 ô · p < 0,00102** |
| §5 · Setup A/B × 2 chiều × bộ lọc bật-tắt | +8 |
| **Sau đợt này** | **58 ô · p < 0,000884** |

Script `liq_factor.py` chạy ở ngưỡng **51 ô** vì lúc đăng ký trước tôi chưa đối
chiếu ô B với bảng cũ. Ngưỡng đó **chặt hơn** mức cần, nên mọi kết luận "không
có lợi thế" ở trên vẫn đứng; không phải chạy lại.

Hai phần đầu của tài liệu này — bác bỏ ước lượng OHLC, và đo chi phí/công suất
— **không cộng ô nào**: không tham số nào được chọn theo kết quả, và không chiến
lược nào được đề xuất. Đó là hiệu chỉnh chi phí cho các ô đã có. Phép đo drift
ở §5 cũng không cộng ô: nó là phép **đo**, không phải phép **chọn**. Các phép
bỏ-một-năm là **xác nhận**, không dùng để chọn.

**Phải nói thẳng về sức mạnh thống kê.** Ở 58 ô, ngưỡng Šidák là
p < 0,000884 (KTC 99,9116%) — một lợi thế thật **+40 bps/lệnh vẫn sẽ trượt**.
Đó là giá của việc cộng dồn 58 ô vào cùng một mẫu. Chính vì vậy §5 đặt phép đo
drift làm bằng chứng chính thay vì bảng bps: drift không tốn ô nên không bị
ngưỡng đó bóp. Nếu còn muốn thử thêm biến thể quét thanh khoản, cách đúng là
tách một mẫu giữ lại chứ không cộng tiếp vào đây.

---

## 5. Quét thanh khoản — Setup A và B (chạy 27/10/2026)

Nghĩa thứ hai của "hướng thanh khoản": giá đi về nơi lệnh chờ đứng sẵn, và cú
xuyên qua mức đó rồi quay lại (Swing Failure Pattern). Đặc tả ICT/SMC được
đưa về dạng code được rồi chạy.

**Vũ trụ: 427 mã có nến 4H**, không phải riêng BTC/ETH — hai mã là hai đường
giá, đúng cái bẫy `touch_bins_multi.py` đã ghi. BTC/ETH báo riêng như tập con.

### Luật (đăng ký trước, không sửa sau khi nhìn số)

Mức thanh khoản, một định nghĩa duy nhất, nhân quả: `SSL = min(low)` và
`BSL = max(high)` trên 20 nến **trước** nến hiện tại; bể đối diện gần 20 nến,
bể xa 60 nến.

**Setup A · Sweep & Reclaim** (mua, bán là ảnh gương): nến quét có
`low < SSL − 0,1×ATR14` và `close > SSL`; xác nhận `close[i+1] > high[i]`; vào
ở close xác nhận; stop `low[i] − 0,25×ATR`; chốt 50% ở bể gần rồi dời stop về
giá vào, 50% còn lại nhắm bể xa; lọc ≥ 2R; giữ tối đa 20 nến. Trong một nến
**kiểm stop trước chốt lời**.

**Setup B · Break & Accept**: `close > BSL` và `volume > 1,5×` TB 20 nến; vào ở
nến test lại đầu tiên trong 5 nến kế (`low ≤ BSL` và `close > open`), không có
thì vào ở close nến `i+5`; stop khi close quay lại dưới `BSL − 0,5×ATR`;
trailing `stop = max(stop, low[j−1])`; chốt ở bể xa.

> **Một chỗ phải lệch khỏi đặc tả.** Đặc tả viết "không có test lại trong 3–5
> nến thì vào ngay ở close nến breakout". Ở nến breakout chưa biết tương lai,
> nên cách diễn đạt nhân quả duy nhất của cùng luật đó là **chờ rồi vào** —
> vào ở nến test lại, hoặc ở `i+5` nếu không có.

**Bộ lọc xu hướng:** close ngày > MA200 ngày cho chiều mua, dùng ngày **đã
đóng** trước nến 4H. Chạy cả hai phía bộ lọc.

**Chi phí:** 10 bps khứ hồi + funding thực (long trả, short nhận).

### Tại sao phép đo chính không phải bảng bps

`touch_drift.py` đã đo 9 mức chốt lời trên 48.620 lệnh và trước phí đều ~0:
mọi luật thoát cho cùng kỳ vọng nếu giá là martingale. Nên câu hỏi thật là
**sau khi quét, lợi suất kỳ vọng có khác 0 không** — nếu không, không luật
thoát nào cứu được, và bảng bps dù đẹp cũng chỉ là hình dạng của luật thoát.

Đối chứng **khớp theo (mã, năm)**: trung bình lợi suất 8 nến của *chính mã đó
trong chính năm đó* lấy trên mọi nến, tức vào lệnh ngẫu nhiên. Đây là đối
chứng đúng; bản đầu tôi trừ trung bình toàn chuỗi, và cách đó tự tạo drift
dương trên mã đang chết.

### Kết quả — bảng bps, KTC 99,9116% (Šidák 58 ô)

| ô | lệnh | thắng | bps/lệnh | KTC đã hiệu chỉnh | |
|---|---|---|---|---|---|
| A·mua · lọc TẮT | 9.721 | 36,0% | **+29,4** | [+3,4 ; +58,7] | qua |
| A·mua · lọc BẬT | 2.097 | 34,0% | −0,2 | [−61,6 ; +74,8] | — |
| A·bán · lọc TẮT | 7.142 | 34,1% | **−38,6** | [−64,0 ; −13,1] | **hại** |
| A·bán · lọc BẬT | 4.722 | 33,3% | **−39,7** | [−67,4 ; −14,1] | **hại** |
| B·mua · lọc TẮT | 52.651 | 36,3% | **−22,2** | [−35,3 ; −6,7] | **hại** |
| B·mua · lọc BẬT | 19.712 | 35,7% | −25,7 | [−51,1 ; +1,8] | — |
| B·bán · lọc TẮT | 49.634 | 39,7% | **−23,8** | [−33,8 ; −13,5] | **hại** |
| B·bán · lọc BẬT | 39.449 | 39,6% | **−19,5** | [−28,8 ; −9,2] | **hại** |

### Kết luận 1 — Setup B chết, và chết theo chiều có hại

Bốn ô của B, với **52.651 và 49.634 lệnh**, mẫu lớn nhất trong cả kho. Ba trong
bốn ô có KTC **không chứa 0 về phía lỗ**: −19,5 đến −23,8 bps mỗi lệnh. Đây
không phải "không tìm thấy lợi thế" mà là **tìm thấy bất lợi, có ý nghĩa thống
kê**, dù ngưỡng đã bị siết tới 99,91%.

Điều này đi ngược kỳ vọng từ Osler mà đặc tả dựa vào ("bằng chứng nghiêng về
tiếp diễn"). Phải nói chính xác cái đã đo: B **không** đo "breakout đi tiếp",
nó đo "mua nhịp test lại của breakout". Drift có điều kiện của B·mua âm ở mọi
chân trời (H=1 −8,1 · H=4 −19,1 · H=8 −12,2 bps, KTC 95% không chứa 0), nên
nhịp test lại sau cú phá vỡ có volume **xấu hơn** vào lệnh ngẫu nhiên.

### Kết luận 2 — A·bán chết, và cũng có hại

−38,6 bps (lọc tắt) và −39,7 bps (lọc bật), cả hai KTC loại 0 về phía lỗ. Quét
đỉnh rồi bán là nghiệp vụ thua tiền. Bất đối xứng với chiều mua rất rõ và nhất
quán qua từng năm (−99, −39, −98, −100 bps các năm 2021–2024).

### Kết luận 3 — A·mua: TÍN HIỆU THẬT, CHIẾN LƯỢC KHÔNG

Đây là phần quan trọng nhất, và nó cần hai bảng mới đọc được.

**Drift có điều kiện, đối chứng khớp (mã, năm), H = 8 nến, n = 9.706:**

```
lợi suất thô sau khi vào   :  +21,8 bps
đối chứng vào ngẫu nhiên   :  −31,6 bps
hiệu (drift thật)          :  +53,4 bps   KTC Šidák [+32,6 ; +78,3]
bỏ 2021                    :  +39,0 bps   KTC Šidák [+17,2 ; +61,7]
```

Drift **sống sót cả ngưỡng Šidák 58 ô và cả phép bỏ 2021**. Cú quét đáy rồi
reclaim thật sự dự báo được: nó hơn vào lệnh ngẫu nhiên trên cùng mã cùng năm
**+39 bps** trong 8 nến.

**Nhưng lợi suất THÔ — thứ vào được tài khoản:**

```
toàn mẫu : +21,8 bps   → trừ 10 bps phí =  +11,8 bps
bỏ 2021  :  +3,0 bps   KTC 95% [−10,4 ; +16,8]  → trừ phí = −7,0 bps
```

Và bảng bỏ-một-năm cho chính luật giao dịch trong đặc tả:

| | lệnh | bps/lệnh | KTC Šidák |
|---|---|---|---|
| toàn mẫu | 9.721 | +29,4 | [+3,4 ; +58,7] |
| **bỏ 2021** | 9.169 | **+2,2** | [−21,5 ; +26,5] — chứa 0 |
| bỏ 2022 | 8.297 | +55,2 | [+27,4 ; +84,0] |
| bỏ 2026 | 7.324 | +17,9 | [−13,9 ; +48,2] — chứa 0 |

**552 lệnh của năm 2021 — 5,7% số lệnh — gánh 93% toàn bộ lợi nhuận.** Bỏ 2021
thì luật trong đặc tả cho +2,2 bps với KTC chứa 0.

Hoà giải hai bảng: drift dương **+39 bps** là *tương đối*, phần lớn đến từ việc
đối chứng âm (−31,6 bps). Vũ trụ 4H gồm cả mã đã huỷ niêm yết, nên vào lệnh
ngẫu nhiên là thua. Cú quét đáy **thua ít hơn mức mã đó thường thua** — và
**không ai gửi "thua ít hơn" vào tài khoản bằng một vị thế MUA**.

### Kết luận 4 — bộ lọc xu hướng không giúp

Đặc tả đặt bộ lọc MA200 ngày làm điều kiện an toàn bắt buộc. Dữ liệu: bật bộ
lọc thì A·mua rụng từ +29,4 xuống **−0,2 bps** và số lệnh còn 2.097, KTC chứa
0. Chưa đủ để nói bộ lọc *có hại* (mẫu nhỏ, KTC rộng), nhưng tuyệt đối không
có bằng chứng nó giúp. Điều khoản an toàn trong đặc tả không được dữ liệu này
xác nhận.

### Hệ quả thực tế

Kết luận của đặc tả là đúng, và lý do còn mạnh hơn nó tưởng:

> dùng bản đồ thanh khoản làm công cụ **định vị**, không làm hệ thống vào lệnh
> độc lập.

Dữ liệu nói chính xác điều đó: có tín hiệu **tương đối**, không có lợi nhuận
**tuyệt đối**. Một lợi thế tương đối chỉ vào được tài khoản qua cấu trúc
**trung tính thị trường** — mua ứng viên quét, bán cả vũ trụ — tức đúng cấu
trúc cắt ngang của chiến lược động lượng đã chốt.

Cho nên hướng đi tiếp **không phải** sửa luật thoát của Setup A (sửa sau khi
nhìn kết quả là khớp tham số), mà là một ô mới có tuyên bố trước: **dùng cú
quét SSL làm lớp định thời điểm vào cho sổ động lượng trung tính**. Chưa chạy.

### Ba điều đợt này KHÔNG chứng minh

1. **Chưa thử PDH/PDL, equal highs, đỉnh/đáy phiên, số tròn, cụm thanh lý.**
   Chỉ dùng một định nghĩa mức: swing 20 nến. Osler đo stop tụ quanh **số
   tròn**, và số tròn là thứ duy nhất trong danh sách có bằng chứng bình duyệt
   — nhưng nó cũng là thứ chưa chạy ở đây.
2. **Chưa dùng OI và funding làm điều kiện phân biệt sweep với breakout.** Đặc
   tả nêu "OI giảm ≥ 3–5% trong nến quét"; kho chỉ có `metrics` cho 54 mã nên
   chạy được nhưng trên vũ trụ nhỏ hơn 8 lần.
3. **Khung 1H chưa chạy.** Kho chỉ có 121 mã ở 1H, bắt đầu 2023-11 — mất sạch
   2021–2022. Và phép tính phí ở `rsi2-connors.md` đã cho thấy hạ khung làm
   biên độ co lại trong khi 10 bps đứng yên.

Script: `scripts/liq_sweep.py`.

---

## 6. Chưa làm

| hướng | trạng thái | chặn lớn nhất |
|---|---|---|
| Quét SSL làm **lớp định thời điểm** cho sổ động lượng trung tính | hướng đi tiếp đáng giá nhất | phải tuyên bố trước; là ô mới |
| Mức là **số tròn** (bằng chứng Osler mạnh nhất) | chưa chạy | không có; chạy được ngay |
| PDH/PDL, equal highs, đỉnh/đáy phiên | chưa chạy | mỗi định nghĩa là thêm ô |
| OI giảm trong nến quét để tách sweep khỏi breakout | chưa chạy | `metrics` chỉ có 54 mã |
| Cụm giá thanh lý (Coinglass/Hyperliquid heatmap) | chưa có dữ liệu | phải tải; xem `docs/dong-tien-cuong-buc.md` |
| Mất cân sổ lệnh / depth lệch bên | chưa chạy | `bookdepth` chỉ có BTCUSDT |
| Quét trong ngày trên nến 1 phút | chưa chạy | `klines1m` chỉ có BTCUSDT |
| Bắt spread / tạo lập | không khả thi ở setup này | cần maker rebate + độ trễ thấp |

Hai thứ cuối cùng đều vướng cùng một chặn: `klines1m` và `bookdepth` **chỉ có
BTCUSDT**, mà một kết luận trên một mã là một đường giá duy nhất.

---

## Script

| Script | Việc |
|---|---|
| `scripts/liq_spread.py` | Hai ước lượng spread từ OHLC — **đã bác bỏ**; giữ làm chứng cứ |
| `scripts/liq_capacity.py` | bookDepth thật, tỷ lệ tham gia, trần công suất |
| `scripts/liq_factor.py` | Amihud + sốc khối lượng làm tín hiệu cắt ngang |
| `scripts/liq_sweep.py` | Setup A (Sweep & Reclaim) + Setup B (Break & Accept), 427 mã 4H |
