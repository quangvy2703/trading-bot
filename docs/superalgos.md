# Hệ thống mẫu của Superalgos — 02/11/2026, LOẠI CẢ SÁU

Nguồn: [github.com/Superalgos](https://github.com/Superalgos). Repo chính chỉ
chứa nền tảng. Các hệ thống giao dịch nằm ở `Algorithmic-Trading-Plugins`
(8 tệp) và `Foundations-Plugins/Workspaces`, chỉ báo ở
`Data-Mining-Plugins` (39 data mine).

## Cách chạy: không chép tay

Mỗi hệ thống là một cây JSON chứa các điều kiện JavaScript
(`chart.at04hs.keltner.lower > chart.at04hs.ebollinger.lower`…). Chép tay hàng
trăm điều kiện thì chắc chắn sai, nên `scripts/superalgos/sa_engine.js` là một
engine nhỏ:

- Chạy **đúng chuỗi điều kiện trong tệp**.
- Chạy **đúng mã chỉ báo** (Procedure Loop) của data mine trong `vm` của
  Node. Context chỉ có `Math`, không có `require` hay `process`, và mã đã được
  soát trước khi chạy.
- Bollinger, %B, kênh / kênh con, EMA, RSI14 viết lại theo mã nguồn
  `BollingerBandsMultiTimeFrameMarket.js` và các procedure của data mine.
- Ngữ nghĩa giai đoạn theo `TradingStages.js` của Superalgos:
  - Có Manage Stage (stop / chốt theo pha): chỉ ra khi chạm stop hoặc chốt,
    đóng ở giá close của nến chạm.
  - Không có Manage Stage: Close Stage mở ngay. Lệnh đóng có điều kiện được
    khớp ở open nến sau.
  - Lệnh vào khớp ở open nến sau.
  - Khung lớn hơn luôn lấy nến **đã đóng** gần nhất.
- Phí 10 bps khứ hồi, không tính funding.
- Giai đoạn 2021-01 → 2026-10.

## Danh mục

| Hệ thống | Logic | Chạy |
|---|---|---|
| **Keltner–Bollinger** | 4H: Keltner (MAMA ± 2 ATR) cắt lên Bollinger (giá điển hình) + SuperTrend lên. Ra khi Bollinger trên vượt Keltner trên, stop 4,5 ATR, chốt 6 ATR (ATR 1H) | BTC + 99 mã |
| **"Cointegration"** | Thật ra không phải đồng liên kết: chênh WMA 15/200 của lợi suất log ÷ σ, khung 3H. Vào khi < −1 và đang lên; ra theo Keltner/Bollinger 4H, stop 5% | BTC + 99 mã |
| **WEMA** | EMA 13 cắt lên EMA 48 (1H) + tín hiệu tổng hợp WEMA ≥ 0,5. Chốt +17%, stop −1% | BTC + 99 mã |
| **MADI** | Độ lệch close − MA20 xuống dưới dải −2σ (60 nến) và RSI14 < 20 (1H). Chốt 3,5 ATR, stop 2 ATR, ra khi độ lệch cắt xuống dải trên | BTC + 99 mã |
| **BB Top Bounce** | 8 chiến lược **bán** đa khung: nến chạm dải trên rồi quay xuống, lọc theo hướng/độ dốc kênh Bollinger 2H–24H; stop 3%, chốt theo pha EMA7 | chỉ BTC* |
| **Weak Hands Buster** | 2 chiến lược **bán** khi BTC gãy dưới dải dưới; stop kéo theo MA, chốt theo 6 pha | chỉ BTC* |
| Lightning Strike | Nến 1 phút, lệnh chờ ở hỗ trợ, bậc chốt 0,1–0,8% | **không chạy**: bậc chốt nhỏ hơn phí khứ hồi; khớp lệnh chờ trên nến 1 phút không mô phỏng được bằng OHLC; 15 phút trước phí đã ≈ 0 (`trong-ngay.md`) |
| LiveTester Chart Scanner | Công cụ quét khung phút chọn khung "tốt nhất" theo một chỉ báo thống kê | **không chạy**: là công cụ, không phải chiến lược |
| DCA Bot | Mua theo mức giá và TP/SL do người dùng nhập tay | **không chạy**: không có tín hiệu để kiểm |

\* Hai hệ thống bán có ngưỡng USD tuyệt đối cho BTC (ví dụ độ lệch 8H
200–1.500 USD, biên độ nến < 750 USD), không áp được cho mã khác.

Vũ trụ là 99 mã có nến 1H trong cache, tức các mã từng vào top 10 thanh
khoản. Cách chọn này hơi thiên vị mã sống sót.

## Luật quyết (`scripts/superalgos_bt.py`, viết trước)

- 10 ô, dùng tham số **gốc** của tác giả, không quét.
- **Null thời điểm:** giữ nguyên mã, chiều và số giờ giữ; đổi giờ vào thành
  ngẫu nhiên; 300 lượt.
- **ĐẠT** khi đủ ba điều kiện:
  1. KTC bootstrap khối 30 ngày, Šidák 10 ô (99,49%), > 0.
  2. p so với null < 0,0051.
  3. ≥ 4/6 năm dương.
- Lưới lân cận chỉ chạy nếu có ô đạt.

## Kết quả

| Ô | Lệnh | bps/lệnh | Thắng | Giữ | KTC 99,49% | Null | p | Năm + | Mã + |
|---|---|---|---|---|---|---|---|---|---|
| Keltner–Bollinger · BTC | 169 | +12,6 | 41% | 44h | [−68 ; +104] | +3,6 | 0,39 | 2/6 | |
| Keltner–Bollinger · 99 mã | 8.592 | +31,5 | 39% | 55h | [−62 ; +120] | +16,3 | 0,077 | 4/6 | 67% |
| Cointegration · BTC | 418 | +5,5 | 53% | 60h | [−59 ; +70] | +12,0 | 0,62 | 4/6 | |
| Cointegration · 99 mã | 26.605 | −1,4 | 45% | 51h | [−54 ; +54] | +14,3 | 1,00 | 2/6 | 48% |
| WEMA · BTC | 581 | −8,3 | 29% | 9h | [−28 ; +16] | −6,7 | 0,56 | 1/6 | |
| WEMA · 99 mã | 35.618 | −4,0 | 31% | 7h | [−16 ; +10] | −6,9 | 0,070 | 0/6 | 41% |
| MADI · BTC | 357 | +3,4 | 43% | 21h | [−35 ; +43] | −2,3 | 0,34 | 3/6 | |
| **MADI · 99 mã** | 21.572 | **+14,6** | 39% | 20h | [−20 ; +51] | −0,8 | **0,000** | 4/6 | 64% |
| BB Top Bounce · BTC | 101 | −32,5 | 41% | 71h | [−137 ; +81] | −39,1 | 0,43 | 2/6 | |
| Weak Hands Buster · BTC | 91 | −63,7 | 25% | 98h | [−195 ; +77] | −42,4 | 0,65 | 1/6 | |

Theo năm (bps/lệnh):

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Keltner–Bollinger · 99 mã | +116 | −63 | +55 | +131 | −67 | +1 |
| MADI · 99 mã | +70 | −43 | +36 | +34 | +13 | −9 |
| BB Top Bounce · BTC | +86 | +35 | −34 | −65 | −45 | −273 |
| Weak Hands Buster · BTC | −105 | −18 | −77 | −165 | +70 | −135 |

**Loại cả mười ô.**

- **Keltner–Bollinger:** +31 bps/lệnh trên 99 mã, nhưng một nửa trong đó là
  phần lời của việc cầm crypto vài ngày (null +16), p = 0,077. Lời dồn vào
  2021 và 2024, hai năm tăng mạnh.
- **MADI là ô duy nhất đáng nhắc.** Nó vượt null thời điểm rất rõ (+14,6 so
  với −0,8 bps, p = 0,000), 64% số mã dương, 4/6 năm dương. Nhưng KTC chứa 0:
  lệnh của 99 mã dồn vào cùng những ngày cả thị trường sập, nên 21.572 lệnh
  thực chất chỉ là vài trăm lần đặt cược độc lập. Đây là bắt đáy ngắn hạn
  trên 1H, cùng họ với RSI(2). RSI(2) trên 1H đã quét 54 ô và loại
  (`rsi2-connors.md`); MADI không thêm gì đủ mạnh để mở lại họ đó.
- **WEMA:** stop 1% trên nến 1H bị nhiễu quét liên tục, 71% số lệnh thua.
- **"Cointegration":** không hơn mua ngẫu nhiên giữ cùng thời gian.
- **Hai hệ thống bán của BTC** lời trong 2021–2022 rồi lỗ đều. Ngưỡng USD
  được chỉnh cho mặt bằng giá BTC lúc viết, nên khi BTC lên giá các ngưỡng mất
  nghĩa. BB Top Bounce có 8 chiến lược con nhưng 6 cái chỉ có 1–19 lệnh trong
  6 năm và S5 không có lệnh nào; chỉ S4 có 49 lệnh, −20 bps. Đó là dấu
  hiệu chỉnh tay khớp với một giai đoạn.

## Lưới tham số × khung thời gian, có nến 1D — 02/11/2026, LOẠI CẢ MƯỜI NHÓM

Theo yêu cầu "thử trên nến 1D" và "quét cả tham số lẫn khung thời gian"
(`scripts/superalgos_grid.py`, luật viết trước trong docstring).

**Khung** (4 mức):

- 1H: bản gốc.
- 4H: mọi khung nhân 4.
- **1D×**: mọi khung nhân 24, giữ tỉ lệ giữa các khung (1H→1D, 4H→4D,
  24H→24D).
- **1D gộp**: mọi khung đều là 1D.

**Tham số:** 3 × 3 quanh bản gốc cho mỗi hệ thống (stop / chốt, ngưỡng vào).

Tổng cộng 10 nhóm × 36 ô = **360 ô**. Lãi ròng đã trừ phí 10 bps và
**funding thật**, vì ở 1D lệnh giữ nhiều ngày nên funding đáng kể. Ô chọn là
ô có lãi ròng làm trơn (ô + lân cận tham số + lân cận khung) cao nhất.
Null max-over-grid tính theo z so với null thời điểm.

| Nhóm | Ô chọn | Lệnh | Ròng bps/lệnh | Null | z | p max-over-grid | Quyết |
|---|---|---|---|---|---|---|---|
| Keltner–Bollinger · BTC | stop 3, chốt 9, 1H | 175 | −2,0 | +4,5 | +0,01 | 1,00 | loại |
| Keltner–Bollinger · 99 mã | stop 4,5, chốt 9, **1D×** | 292 | +1.515 | **+865** | +1,43 | 0,96 | loại |
| Cointegration · BTC | gốc, **1D gộp** | 54 | +264 | +111 | +1,12 | 0,98 | loại |
| Cointegration · 99 mã | rm < −0,5, stop 0,97, 1H | 40.156 | −2,1 | +8,8 | −1,89 | 1,00 | loại |
| WEMA · BTC | gốc, 1H | 581 | −8,8 | −6,0 | −0,21 | 1,00 | loại |
| WEMA · 99 mã | chốt 1,30, stop 0,99, **1D** | 1.306 | +90,6 | +28,7 | +2,02 | 0,57 | loại |
| MADI · BTC | RSI < 15, 5/3 ATR, 1H | 171 | −11,5 | −1,5 | −0,34 | 1,00 | loại |
| MADI · 99 mã | RSI < 15, 5/3 ATR, **1D** | 360 | +230 | **+285** | −0,19 | 1,00 | loại |
| BB Top Bounce · BTC | stop 1,05, chốt 0,95, 1H | 89 | +5,6 | −51 | +0,69 | 1,00 | loại |
| Weak Hands Buster · BTC | stop 1,02, kéo 0,97, 1H | 102 | −31,2 | −30,2 | −0,13 | 0,99 | loại |

Đọc bảng:

- **Số lớn ở 1D là ảo giác của việc cầm lâu.** Lệnh 1D giữ nhiều ngày đến
  nhiều tuần trên các mã crypto từng vào top 10, mà mua ở giờ ngẫu nhiên rồi
  giữ cùng thời gian cũng lời +285 … +865 bps. Keltner–Bollinger 1D× +1.515
  bps chỉ hơn null 0,4 lần độ lệch chuẩn của null. MADI 1D (+230) còn **kém
  hơn** mua ngẫu nhiên (+285). Khoảng tin cậy rộng hàng nghìn bps.
- **Chỉ WEMA trên 99 mã ở 1D là có z > 2** (+90,6 so với null +28,7). Nhưng
  đó là ô tốt nhất trong 36 ô; tính max-over-grid thì p = 0,57.
- **1H vẫn ≈ 0** ở mọi tham số, đúng như lần chạy bản gốc.
- WEMA và MADI chỉ dùng khung 1H, nên 1D× và 1D gộp cho kết quả giống hệt nhau
  (36 ô trùng; vẫn cộng vào kế toán). Trên BTC, phần lớn ô 1D có dưới 30 lệnh
  nên để trống.
- Không ô nào đạt, nên không cần bước kiểm 6 cách cắt ngày.

Kế toán: **+360 ô → 1.239**.

## Keltner–Bollinger 1D so với mua giữ rổ thanh khoản — 02/11/2026, LOẠI

Ô +1.515 bps/lệnh ở trên được thử lại cho đúng (`scripts/superalgos_kb_bench.py`,
luật viết trước):

- **Vũ trụ:** 623 mã, gồm cả mã đã huỷ niêm yết. Lệnh chỉ được tính khi mã
  đang nằm trong top N thanh khoản tại ngày tín hiệu.
- **So sánh:** với rổ mua đều top N **cùng cửa sổ** giữ lệnh. A = lệnh − rổ.
- **Lưới 36 ô:** tham số 3×3 × khung {1D×, 1D gộp} × N {20, 50}.
- **Null:** thay mã bằng một mã ngẫu nhiên trong rổ cùng ngày; dùng
  max-over-grid.

| | Lệnh ròng | Rổ cùng cửa sổ | A (chọn mã) | So với mua giữ rổ thường |
|---|---|---|---|---|
| Ô cũ trên 99 mã sống sót | +1.515 | — | — | — |
| Cùng ô, vũ trụ đúng thời điểm, top 50 | **−363** | −659 | +295 | −212 |
| Ô 1D gộp tốt nhất, top 20 | +181 | +34 | +147 | +166 |

**Loại** (✗✗✓✓). Ô chọn có A +295, KTC [−588 ; +1.307], z +1,00,
p max-over-grid 0,999.

- **+1.515 là thiên lệch sống sót.** Thêm mã chết và chỉ tính mã đang thanh
  khoản thì cùng ô đó **lỗ −363 bps/lệnh**. Trung vị một lệnh là −20%, chỉ
  26% số lệnh thắng.
- **A dương ở cả 36/36 ô, nhưng chỉ nhờ vài lệnh bơm.** Bỏ 5 lệnh tốt nhất
  là A âm ở **mọi** ô. Không ô nào có z vượt 1,5, và p max-over-grid ≥ 0,94.
- **Hệ thống chọn thời điểm tệ.** Ở khung 1D×, nó vào đúng lúc cả thị trường
  sắp giảm: rổ cùng cửa sổ −283 … −674 bps, tức chọn thời điểm khoảng −500
  bps/lệnh. Điểm vào là lúc "squeeze bung ra", và trên 1D lúc đó thường là
  đỉnh.

Kế toán: **+36 ô → 1.275**.

## Chỉ trên top 20 như động lượng + chọn lại tham số mỗi ngày — 02/11/2026, LOẠI

`scripts/superalgos_top20.py`, luật viết trước.

- **Vũ trụ:** giống hệt động lượng. 623 mã gồm cả mã chết, hạng thanh khoản
  theo trung vị 30 ngày trượt, top 20, có ≥ 205 nến.
- **Dữ liệu:** nến 1H tải mới đủ cho cả 139 mã từng ở top 20
  (`scripts/fetch_top20_1h.py` → `reports/.cache/uni_tf/1h_top20/`). Cache cũ
  chỉ phủ 70%, ETH bị cắt ở 2023-10.
- **Thước đo:** A = lệnh − rổ đều top 20 cùng cửa sổ, cả hai trừ phí và
  funding.
- **Lưới:** 4 hệ thống × tham số 3×3 × khung {1H, 4H, 1D×, 1D gộp} = 144 ô.

| Hệ thống | Ô chọn | Lệnh | A bps | Lệnh ròng | KTC A (99,86%) | z | p max-over-grid |
|---|---|---|---|---|---|---|---|
| Keltner–Bollinger | stop 3, chốt 4, 1D× | 88 | +178 | −123 | [−375 ; +808] | +0,64 | 1,00 |
| Cointegration | rm < −1,5, stop 0,90, 1D× | 162 | +317 | +480 | [−428 ; +1.246] | +1,47 | 0,93 |
| **WEMA** | chốt 1,30, stop 0,99, **1D** | 322 | **+120** | +208 | [−30 ; +319] | **+2,13** | 0,52 |
| MADI | RSI < 30, 2,5/1,5 ATR, 1H | 10.266 | −2 | −2 | [−13 ; +8] | −0,50 | 1,00 |

**Loại cả bốn.** Ô gần nhất là **WEMA 1D**:

- A dương ở 9/9 bộ tham số (+79 … +120), dương 5/6 năm.
- Bỏ 5 lệnh tốt nhất vẫn còn +30.
- Nhưng z 2,13 là ô tốt nhất trong 36 ô, tính max-over-grid thì p = 0,52, và
  KTC chứa 0.

Ở 1D, WEMA là: EMA 13 cắt lên EMA 48 trên nến ngày, kèm tín hiệu tổng hợp
WEMA ≥ 0,5, chốt +17 … +30%, stop −1 … −5%. Thực chất là bám xu hướng nhanh
với stop rất chặt. Đáng giữ trong danh sách ý tưởng, nhưng chưa đủ bằng chứng.

Nhận xét sau khi đã xem bảng (không đăng ký trước, không dùng để quyết):
Keltner–Bollinger ở 4H có A dương ở cả 9/9 bộ tham số (+51 … +127). Nếu muốn
theo, phải làm thành phép thử mới có đăng ký trước, và tính cả 144 ô này vào.

**Chọn lại tham số × khung mỗi ngày** từ L ngày trước (90 / 180 / 365), theo
tổng lãi ròng các lệnh đã đóng:

| Hệ thống | Gốc 1H cố định, A | WFO L180, A | KTC 99,375% | Đổi ô |
|---|---|---|---|---|
| Keltner–Bollinger | −6 | +11 | [−77 ; +124] | 193 |
| Cointegration | −6 | −36 | [−117 ; +44] | 181 |
| WEMA | +7 | +8 | [−7 ; +24] | 196 |
| MADI | −9 | −15 | [−38 ; +2] | 221 |

**Loại cả bốn.** WFO không hơn bản gốc cố định một cách đáng kể, và thua
"lấy trung bình 36 ô" ở cả bốn hệ thống. Nó đổi ô khoảng 200 lần trong 6 năm,
liên tục đuổi theo ô vừa gặp may, giống hệt kết quả với RSI(2)
(`rsi2-connors.md`).

Kế toán: **+144 ô lưới + 12 ô meta → 1.431**.

## Data mine: 39 bộ chỉ báo

Data mine chỉ là chỉ báo (Alligator, Chande, Heikin-Ashi, Turtles, Fibonacci,
Mayer Multiple, RVI, VWAP neo, phân kỳ, MACD, SuperTrend, MAMA, Holt–Winters,
sóng sin…), không có luật vào ra riêng. Phần lớn trùng với các họ đã thử
(Turtles = Donchian, đã chết; Bollinger / z-score, đã loại; MA cắt nhau, đã
chết). Không quét từng chỉ báo thành tín hiệu: vài trăm chỉ báo nhân lưới
tham số trên cùng dữ liệu là đúng kiểu data snooping mà Deflated Sharpe vừa
cảnh báo (`chien-luoc-pho-bien.md`).

## Kế toán

10 ô, cộng vào kế toán cắt ngang: **869 → 879**.

## Tệp

| Tệp | Việc |
|---|---|
| `scripts/superalgos/sa_engine.js` | Engine nhỏ: chạy điều kiện JS của hệ thống + mã chỉ báo data mine trong `vm` |
| `scripts/superalgos/products.py` | Trích mã chỉ báo từ JSON data mine → `products.json` |
| `scripts/superalgos/README.md` | Cách tải dữ liệu và chạy lại |
| `scripts/superalgos_bt.py` | Thống kê, null thời điểm, luật quyết (tham số gốc, 1H) |
| `scripts/superalgos_top20.py`, `scripts/fetch_top20_1h.py` | Top 20 như động lượng: lưới tham số × khung + chọn lại mỗi ngày |
| `scripts/superalgos_kb_bench.py` | Keltner–Bollinger 1D so với rổ top N đúng thời điểm (gồm mã chết) |
| `scripts/superalgos_grid.py` | Lưới tham số × khung (1H / 4H / 1D× / 1D gộp), null max-over-grid |
