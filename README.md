# Trang quản lý chạy thật

Một trang web duy nhất để vận hành hai chiến lược đã chốt:

- **RSI(2) Connors v2** — [docs/rsi2-connors.md](../docs/rsi2-connors.md)
- **Động lượng cắt ngang điều chỉnh biến động** — [docs/xsmom-volnorm.md](../docs/xsmom-volnorm.md)

Toàn bộ chạy trong Docker: **một dịch vụ, một ổ đĩa, một cổng**.

```bash
cd live
cp .env.example .env          # sửa nếu cần; để trống vẫn chạy được sổ giấy
docker compose up -d --build
open http://127.0.0.1:8777
```

Lần khởi động đầu tự **gieo mầm** kho nến từ `../reports/.cache/uni1d`
(mount chỉ-đọc) trong luồng nền — khoảng 580.000 nến, 2–3 phút. Bỏ dòng mount
đó thì hệ tự tải từ Binance, lâu hơn nhiều.

## Mặc định là SỔ GIẤY

Hệ **không đặt lệnh thật** cho tới khi mở **cả ba** khoá:

| # | Khoá | Mở bằng cách |
|---|---|---|
| 1 | `LIVE_TRADING_ENABLED=1` | sửa `docker-compose.yml` rồi `docker compose up -d` |
| 2 | Khoá API có quyền giao dịch | đặt `BINANCE_API_KEY` / `BINANCE_API_SECRET` |
| 3 | Công tắc trong UI | gõ đúng **`TÔI ĐỒNG Ý CHẠY THẬT`** rồi bấm *Bật* |

Khoá 1 nằm ở **tầng mã**: thiếu nó thì hàm đặt lệnh thật ném lỗi ngay cả khi
gọi thẳng trong container, không đi qua UI. Thiết kế thế để một cú bấm nhầm
trong trình duyệt không thể chạm vào tiền.

`BINANCE_ENV=testnet` (mặc định) trỏ vào Binance Futures testnet — tiền giả
nhưng đi hết đường ống thật: ký API, làm tròn khối lượng theo `stepSize`,
trượt giá, lệnh hỏng. Đổi sang `live` là đổi sang tiền thật.

### Tài khoản phải đặt đúng trước

- **Chế độ vị thế MỘT CHIỀU (one-way).** Mã không gửi `positionSide` và dùng
  `reduceOnly` để đóng; ở chế độ hai chiều Binance từ chối hết với `-4061`.
  Lúc bật công tắc hệ gọi `/fapi/v1/positionSide/dual` kiểm trước và **từ chối
  bật** nếu tài khoản đang ở Hedge — để lỗi lộ ra lúc bấm nút, không phải lúc
  00:05 UTC.
- **Đòn bẩy và kiểu ký quỹ** hệ **không** đặt, dùng mặc định của từng mã trên
  tài khoản. Tự đặt trước.
- **Khoá API**: bật Futures, **tắt rút tiền**, khoá theo IP.
- **`START_EQUITY_USD` phải bằng số tiền thật sự nạp.** Cỡ lệnh tính bằng
  `START_EQUITY_USD × tỷ trọng`, không đọc số dư từ sàn (xem § KHÔNG làm).

## Một ngày chạy thế nào

Lịch mặc định **00:05 UTC**, ngay sau khi nến 1D đóng lúc 00:00 — đúng quy ước
của backtest (*chốt tín hiệu ở `close`, khớp ở `open` nến kế tiếp*). Chạy xong
là khớp luôn, nên độ lệch so với backtest là nhỏ nhất.

```
1. tải nến mới cho các mã đang niêm yết
2. xếp hạng thanh khoản (trung vị giá trị giao dịch USD trượt 30 ngày)
3. RSI(2) : đóng vị thế chạm stop hoặc RSI>70, rồi lấp chỗ trống bằng tín hiệu mới
4. động lượng : đúng MỘT sổ trong bảy tái cân bằng hôm nay, sáu sổ kia giữ nguyên
5. sổ mục tiêu → việc cần làm → đặt lệnh (giấy hoặc thật)
6. đánh giá lại vốn theo giá hiện tại, ghi nhật ký
```

Vốn chia theo `ALLOC_RSI2` / `ALLOC_XSMOM` (mặc định 50/50). Mỗi vị thế
RSI(2) bằng `ALLOC_RSI2 / 5`; mỗi vị thế động lượng bằng
`ALLOC_XSMOM / 28` (7 sổ × 2 mua + 2 bán). Tổng tỷ trọng tuyệt đối ≤ 100%,
ròng ≈ 0 ở phần động lượng.

## Config nào của chiến lược nào

**24 tham số, bốn nhóm.** Hai nhóm riêng từng chiến lược, hai nhóm dùng chung.

### Riêng RSI(2) — 9 ô

| tham số | chốt | nghĩa |
|---|---|---|
| `rsi2.topn` | 10 | vũ trụ top N thanh khoản |
| `rsi2.slots` | 5 | số chỗ tối đa |
| `rsi2.rsi_in` | 10 | vào khi RSI(2) < |
| `rsi2.rsi_out` | 70 | thoát khi RSI(2) > |
| `rsi2.ma` | 20 | lọc xu hướng close > MA |
| `rsi2.atr` | 14 | chu kỳ ATR |
| `rsi2.atr_k` | 6,0 | bội ATR cho cắt lỗ |
| `rsi2.cap` | 0,40 | trần cắt lỗ |
| `rsi2.min_bars` | 205 | số nến lịch sử tối thiểu |

### Riêng động lượng cắt ngang — 8 ô

| tham số | chốt | nghĩa |
|---|---|---|
| `xsmom.topn` | 20 | vũ trụ top N thanh khoản |
| `xsmom.lookback` | 30 | chân trời chấm điểm (ngày) |
| `xsmom.frac` | 0,10 | tỷ lệ mỗi chân |
| `xsmom.legs` | 2 | số mã tối thiểu mỗi chân |
| `xsmom.sleeves` | 7 | số sổ lệch ngày |
| `xsmom.hold` | 7 | số ngày giữ / nhịp tái cân bằng |
| `xsmom.min_bars` | 205 | số nến lịch sử tối thiểu |
| `xsmom.ma` | 30 | lọc xu hướng — 0 là tắt |

**Hai nhóm trên trùng tên nhưng KHÔNG dùng chung giá trị.** `rsi2.topn = 10`
và `xsmom.topn = 20` là hai vũ trụ khác nhau; `rsi2.ma = 20` lọc theo MA20
còn `xsmom.ma = 30` lọc theo MA30. Tiền tố quyết định tất cả.

### Bật/tắt từng chiến lược — 2 ô

| tham số | biến môi trường | chốt |
|---|---|---|
| `alloc_rsi2` | `ALLOC_RSI2` | 1,0 — **chỉ RSI(2)** |
| `alloc_xsmom` | `ALLOC_XSMOM` | 1,0 — **chỉ động lượng** |

Hệ số nhân cho 1R của riêng chiến lược đó. **0 = tắt**, và vị thế đang mở của
nó bị đóng ở lượt kế tiếp.

### Dùng chung cả hai — 5 ô

| tham số | biến môi trường | chốt | chặn gì |
|---|---|---|---|
| `risk_r_usd` | `RISK_R_USD` | 100 | 1R — số USD rủi ro mỗi lệnh |
| `risk_max_open` | `RISK_MAX_OPEN` | 28 | số vị thế mở cùng lúc |
| `max_order_usd` | `MAX_ORDER_USD` | 200 | giá trị **một lệnh** |
| `max_gross_usd` | `MAX_GROSS_USD` | 1.000 | **tổng** mở thêm mỗi lượt |
| `max_orders_per_run` | `MAX_ORDERS_PER_RUN` | 40 | **số lệnh** mỗi lượt |

Năm ô này **không phân biệt chiến lược** — một lệnh RSI(2) và một lệnh động
lượng ăn chung hạn mức. Trần `risk_max_open = 28` là tổng của cả hai, không
phải 28 mỗi bên.

### Đặt ở đâu

| nhóm | tab Cấu hình | biến môi trường |
|---|---|---|
| riêng RSI(2) · riêng động lượng | **có** | **không** |
| bật/tắt · dùng chung | **có** | **có** |

Tham số riêng từng chiến lược **cố ý không mở qua biến môi trường**: hai bộ
này được chọn kèm kế toán đa phép thử (49 ô cắt ngang, ngưỡng Šidák 0,00105),
nên đổi chúng phải đi qua UI — nơi có băng cảnh báo lệch và ghi nhật ký — chứ
không lặng lẽ qua `docker-compose.yml`.

## Cỡ lệnh — đơn vị R

Từ 26/10/2026 hệ định cỡ theo [đơn vị R](../docs/money-management-r.md), không
còn chia đều vốn:

```
cỡ lệnh (USD) = RISK_R_USD / R
   RSI(2)      R = (giá vào − cắt lỗ) / giá vào      ← thường 40% (trần stop)
   động lượng  R = độ lệch chuẩn log 30n × √số ngày giữ
```

`RISK_R_USD` mặc định **100** — mỗi lệnh mất đúng chừng đó khi chạm điểm thua.
**Vốn không quyết định cỡ lệnh**, nó chỉ quyết định mở được bao nhiêu lệnh
cùng lúc; trần đó là `RISK_MAX_OPEN` (mặc định **28** = 7 sổ × 4 vị thế).

Cỡ lệnh tỷ lệ **nghịch** với rủi ro một đơn vị hàng. Số thật lấy từ hệ đang
chạy:

```
SOLUSDT   σ ngày  1,86%  → R(7n)  4,9%  → cỡ 2.037 USD
DOGEUSDT  σ ngày  2,23%  → R(7n)  5,9%  → cỡ 1.697 USD
PUMPUSDT  σ ngày  7,47%  → R(7n) 19,8%  → cỡ   506 USD
QNTUSDT   σ ngày 15,41%  → R(7n) 40,8%  → cỡ   245 USD
```

Cả bốn đều rủi ro đúng 100 USD. Một sổ ngốn ~4.500 USD giá trị hợp đồng, bảy
sổ ~31.000 USD — khớp với dải 21.000–47.000 của backtest.

Lãi/lỗ vì thế là **phép cộng theo USD**, không còn gộp lãi theo tỷ lệ.

### Bật / tắt từng chiến lược

`ALLOC_RSI2` và `ALLOC_XSMOM` **không còn là tỷ trọng vốn** — định cỡ theo R
không chia vốn cho ai cả. Chúng là **hệ số nhân cho 1R** của từng chiến lược:

```
1R thực tế của RSI(2)     = RISK_R_USD × ALLOC_RSI2
1R thực tế của động lượng = RISK_R_USD × ALLOC_XSMOM
0 = TẮT chiến lược đó
```

Tắt không phải là "ngừng mở lệnh mới": lượt chạy kế tiếp **đóng sạch vị thế
đang mở** của chiến lược đó. Bỏ qua kiểu "không nhắc tới" sẽ để chúng mở mãi
mà không ai tái cân bằng — đúng cái bẫy đã gặp khi giảm số sổ lệch ngày.

Hệ từ chối tắt cả hai: *«tắt cả hai chiến lược thì không còn gì để chạy»*.

**Chạy mỗi động lượng:** tab Cấu hình → `alloc_rsi2` = **0** → Lưu. Hoặc để
vĩnh viễn thì đặt `ALLOC_RSI2: "0"` trong `docker-compose.yml` rồi dựng lại.

### Bộ lọc xu hướng của động lượng

`xsmom.ma = 30` — chỉ MUA nếu close > MA30, chỉ BÁN nếu close < MA30.
**Đã chốt 26/10/2026.** Ứng viên không qua lọc bị **bỏ hẳn**, không thay bằng
mã kế tiếp — nên sổ thường còn **3,27 vị thế mỗi kỳ** thay vì 4, và có kỳ chỉ
còn một chân.

Lưới 10/14/20/30/50/100/200 cho CAGR/sụt đơn đỉnh, cực đại đúng tại 30. Đặt 0
để tắt. Lưu ý: KTC của phần cải thiện **vẫn chứa 0** — đây là lựa chọn vận
hành, không phải kết luận thống kê (xem `docs/xsmom-volnorm.md`).

### 1R phải tương xứng với vốn

Trên dữ liệu thật R nằm trong khoảng **4,9% – 40,8%**, nên:

```
cỡ một lệnh  ≈  2,5 × đến 20 × 1R
phơi nhiễm 7 sổ  ≈  300 × 1R
```

Với `RISK_R_USD=100` thì cần khoảng **31.000 USD** giá trị hợp đồng. Ngược
lại, có vốn V thì **1R ≈ V / 300** là điểm khởi đầu.

Bộ trần đi kèm, cho **động lượng chạy một mình** (7 sổ × 4 vị thế):

| vốn | `RISK_R_USD` | `MAX_ORDER_USD` | `MAX_GROSS_USD` | `RISK_MAX_OPEN` |
|---|---|---|---|---|
| 5.000 | 10 | 250 | 5.000 | 28 |
| 20.000 | 40 | 1.000 | 20.000 | 28 |
| 50.000 | 100 | 2.500 | 50.000 | 28 |

Quy tắc: `MAX_ORDER ≈ 25 × 1R` (lệnh lớn nhất quan sát được là 20×) và
`MAX_GROSS ≈ 500 × 1R` (đỉnh phơi nhiễm backtest là 470×). Đặt thấp hơn thì
chính các vị thế biến động thấp — nhóm cỡ lệnh lớn nhất — sẽ bị chặn, mà đó
không phải nhóm đáng bỏ.

**Trần mặc định `MAX_ORDER_USD=200` và `MAX_GROSS_USD=1000` được đặt cho cách
chia đều vốn cũ** — để nguyên với `1R=100` thì **mọi lệnh động lượng đều bị
chặn**. Trang có cảnh báo đỏ ngay ở ô «Thao tác» khi hai con số này lệch
nhau, nên lỗi lộ ra trước khi tới giờ chạy chứ không phải sau.

Cả hai đều sửa được trong tab Cấu hình mà không cần dựng lại ảnh.

## Trần rủi ro

Áp **ở tầng mã, trước khi gửi bất kỳ lệnh nào**; vượt trần thì lệnh bị chặn
và hiện ở cột *ghi chú* trong bảng «việc cần làm».

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `MAX_GROSS_USD` | 1000 | tổng giá trị mở thêm trong một lượt |
| `MAX_ORDER_USD` | 200 | giá trị một lệnh |
| `MAX_ORDERS_PER_RUN` | 40 | số lệnh mở mỗi lượt |

Lệnh **đóng** vị thế không bao giờ bị chặn — trần chỉ hạn chế mở thêm.

**Dừng khẩn** tắt công tắc rồi đóng sạch vị thế đang mở.

## Giao diện

Giao diện là **kính sáng trên nền pastel**: một tấm nền gradient đứng yên khi
cuộn, ứng dụng nổi lên trên dưới dạng tấm kính mờ bo 26px, các thẻ là trắng
bán trong có viền sáng. Nhấn màu là tím `#6D5BD0`. Mọi màu chữ đã đo trên
trang thật: chữ chính 14,3:1 · nhãn mờ 5,0:1 · chữ trắng trên nút tím 5,2:1 ·
chip trên nền pastel 5,6–6,6:1 — đều qua ngưỡng AA. Ô dính trái của bảng và
hàng tiêu đề dùng màu **đục**, không bán trong, nếu không nội dung cuộn qua
sẽ hiện xuyên qua nó.

Trang là một tệp tĩnh duy nhất, `app/static/index.html` — không build, không
phụ thuộc mạng ngoài (chữ số dùng font mono sẵn có của máy, không tải Google
Fonts). Sửa xong phải **dựng lại ảnh** thì container mới thấy, vì `Dockerfile`
chép thẳng `app/` vào ảnh:

```bash
docker compose up -d --build
```

Cơ chế cho màn hẹp — đã soi ở 1440 / 1280 / 1024 / 860 / 768 / 560 / 390 px,
không chỗ nào làm cả trang cuộn ngang:

| chỗ | cơ chế |
|---|---|
| dải trạng thái trên cùng | cuộn ngang trong khung riêng, mờ dần mép phải dưới 760px |
| dàn số liệu phụ | lưới hairline 4 → 2 cột |
| hai cột chính | gộp thành một cột dưới 1060px; ở bảng điều khiển cụm công tắc lên trước |
| mọi bảng | cuộn ngang trong khung riêng, cột đầu dính lại để không mất ngữ cảnh |
| bảng cấu hình | cuộn ngang trong khung riêng, ô nhập co từ 104px xuống 60px |
| tab phương pháp | cột đọc kẹp 880px và canh giữa; mục lục gập hẳn dưới 1100px |
| nút & ô nhập | cao tối thiểu 44px dưới 680px |

Chuyển động chỉ còn một chỗ (đèn đỏ nhấp nháy khi đang chạy thật) và nó tắt
khi máy bật `prefers-reduced-motion`.

## Bốn tab

**Bảng điều khiển** — vốn, sụt, vị thế, lượt chạy, ba đèn khoá, việc cần làm,
đường vốn, bảng vị thế.

**Phương pháp** — đọc thẳng hai bản đặc tả đã chốt trong trang:
`docs/rsi2-connors.md` và `docs/xsmom-volnorm.md`. Thư mục `docs/` được gắn
vào container ở `/docs` **chỉ đọc**, nên sửa tài liệu là trang thấy ngay, không
phải dựng lại ảnh. Markdown do chính trang dựng (một trình tối thiểu ~90 dòng)
— không kéo thư viện ngoài, trang vẫn chạy khi máy không có mạng. Liên kết
`.md` giữa các tài liệu bấm được, mở ngay trong tab; từ 1100px trở lên có mục
lục dính bên phải tự sáng theo mục đang đọc.

Đường dẫn tài liệu đi qua allowlist tên (`^[a-z0-9][a-z0-9.-]{0,63}$`) và kiểm
lại kết quả resolve có còn nằm trong `/docs` không, nên `..%2f..%2fetc%2fpasswd`
trả 404 chứ không đọc được gì ngoài thư mục đó.

**Cấu hình** — sửa được 24 tham số lúc chạy: phân bổ vốn, toàn bộ tham số
RSI(2), toàn bộ tham số động lượng, trần rủi ro. Mỗi dòng hiện **giá trị đã
chốt trong docs** bên cạnh **giá trị đang dùng**; dòng nào đúng bộ chốt thì
làm mờ, dòng nào đang lệch thì gạch ngang giá trị chốt và kẻ vạch vàng ở mép
trái, ô nào đang sửa thì viền vàng.

Vì sao làm vậy: hai bộ tham số được chọn kèm kế toán đa phép thử (36 ô cắt
ngang, ngưỡng Šidák 0,00135). Đổi một con số là kết quả thật **không còn được
bảo chứng bởi nghiên cứu**. Nên hệ luôn nói rõ đang lệch bao nhiêu ô — một
băng cảnh báo trong tab và một huy hiệu đỏ trên tên tab — và ghi mọi thay đổi
vào nhật ký (`đổi tham số rsi2.slots: 5 → 3`). Nút **Trả về bộ đã chốt** đưa
tất cả về nguyên trạng.

Kiểm tra ở phía máy chủ, không chỉ trong trình duyệt:

```
rsi2.slots = 99          → «số chỗ (N)» phải nằm trong [1, 50], nhận 99
alloc 0,9 + 0,9          → tổng phân bổ vốn 1.80 > 1,00 — tổng tỷ trọng
                           tuyệt đối sẽ vượt 100% vốn
xsmom.sleeves ≠ hold     → số sổ phải bằng số ngày giữ, nếu không các sổ sẽ
                           chồng lấn hoặc để hở ngày không có sổ nào tái cân bằng
tham số không tồn tại    → không có tham số «…»
```

Giảm **số sổ** khi đang có vị thế ở sổ cũ thì những vị thế đó được **đóng ở
lượt kế tiếp**, không bị bỏ rơi (chúng sẽ không bao giờ tới lượt tái cân bằng
nữa). Ghi chú của lượt chạy hiện «sổ quá hạn bị đóng».

**Nhật ký** — lệnh gần đây, sự kiện, các lượt chạy.

## Trang có gì

Vốn · sụt khỏi đỉnh · vị thế đang mở · lượt chạy cuối và kế tiếp · tình trạng
kho dữ liệu · ba đèn khoá · **việc cần làm** (sổ mục tiêu trừ sổ hiện tại,
kèm lý do từng dòng và lý do bị chặn) · đường vốn · bảng vị thế · lệnh gần
đây · nhật ký. Tự làm mới mỗi 30 giây.

«Xem trước» tính sổ mục tiêu mà **không** đặt lệnh — dùng để nhìn trước khi
bấm «Chạy ngay».

## Đã kiểm

- Chỉ báo trong container (`app/indicators.py`) khớp **tuyệt đối** bản nghiên
  cứu: SMA20, RSI(2) Wilder, ATR14, trung vị trượt 30 ngày — lệch 0 điểm.
- Bộ sinh tín hiệu khớp **từng bit** với `scripts/rsi2_universe.py` trên cùng
  một ngày: thứ tự xếp hạng thanh khoản, RSI, MA20, ATR, trung vị giá trị
  giao dịch đều lệch 0.
- Ba chốt chặn chạy thật đều từ chối đúng, kể cả khi gọi thẳng hàm đặt lệnh
  trong container.
- Trang không cuộn ngang ở 1440/1280/1024/860/768/560/390 px trên **cả ba tab**; bảng rộng cuộn
  trong khung riêng.

## Điều trang này KHÔNG làm

- **Không** đo trượt giá hay tác động thị trường — backtest chưa đo, chạy thật
  cũng chưa.
- **Không** đối soát vị thế với sàn. Sổ nội bộ là nguồn sự thật; nếu bạn vào
  lệnh tay trên cùng tài khoản, hai bên sẽ lệch. `Trader.account()` và
  `Trader.positions()` đã viết sẵn nhưng chưa chỗ nào gọi.
- **Không** đọc số dư thật để tính cỡ lệnh. Vốn là con số nội bộ: mốc cuối
  trong bảng `equity` của chế độ đó, chưa có thì rơi về `START_EQUITY_USD`.
- **Không** có đăng nhập. Cổng chỉ mở trên `127.0.0.1` — đừng bao giờ đưa ra
  ngoài.
- **Không** tự khởi động lại chiến lược khi dữ liệu thiếu; lượt chạy hỏng được
  ghi trạng thái «hỏng» và dừng.

## Hai chốt chặn cho sổ nội bộ khỏi lệch với sàn

**Lệnh không khớp không được ghi sổ.** Lệnh bị sàn từ chối (`lỗi`) hoặc dưới
mức tối thiểu (`bỏ qua`) trước đây vẫn được ghi là đã mở / đã đóng — sổ và sàn
lệch ngay lượt đầu, và lượt sau hệ sẽ gửi `reduceOnly` đóng một vị thế không
tồn tại. Giờ chỉ lệnh thật sự khớp mới vào sổ; số còn lại đếm riêng, hiện ở
thẻ *Lượt chạy* và ghi vào nhật ký (`không khớp, bỏ khỏi sổ: …`).

**Không mở ngược chiều trên mã đang giữ** (chỉ ở chế độ thật). Hai sổ lệch
ngày của động lượng có thể vừa mua vừa bán cùng một mã; trong sổ nội bộ đó là
hai vị thế, nhưng sàn một chiều bù trừ chúng thành một. Hậu quả nằm ở lúc
đóng: `reduceOnly` trên phần đã bị bù trừ bằng 0 sẽ bị từ chối và vị thế kẹt
lại trong sổ vĩnh viễn. Lệnh mở gây xung đột bị chặn và hiện lý do trong
*Việc cần làm*. **Cùng chiều thì không chặn** — sàn gộp khối lượng, và lệnh
đóng có ghi rõ khối lượng nên vẫn trừ đúng phần của từng sổ.

Giá phải trả: ở chế độ thật, thỉnh thoảng một chân của động lượng bị bỏ, nên
danh mục thật lệch nhẹ so với backtest. Sổ giấy giữ nguyên hành vi cũ để còn
so được. Cách vá triệt để là bù trừ khối lượng theo từng mã ở tầng đặt lệnh,
hoặc chuyển sang chế độ hai chiều và gửi `positionSide` — cả hai đều lớn hơn
nhiều và chưa làm.

## Nhắc lại giới hạn của chính hai chiến lược

Cả hai **chưa có kiểm định ngoài mẫu sạch**. RSI(2) từng âm khỏi đỉnh **373
ngày**; động lượng cắt ngang **661 ngày (21,7 tháng)** và 94% số ngày nằm
dưới đỉnh cũ. Danh mục 50/50 trong backtest cho CAGR 50,3% với sụt 24,6%,
nhưng đợt chìm dài nhất vẫn **645 ngày**. Đây là lý do mặc định là sổ giấy.

## Tệp

| Tệp | Việc |
|---|---|
| `docker-compose.yml`, `Dockerfile` | một dịch vụ, ổ đĩa `livedata`, cổng 127.0.0.1:8777 |
| `app/config.py` | cấu hình từ biến môi trường + tham số hai chiến lược |
| `app/db.py` | SQLite + WAL, một người ghi |
| `app/binance.py` | API công khai (dữ liệu) và API có ký (đặt lệnh) |
| `app/data.py` | gieo mầm, tải bổ sung, lọc perp-crypto |
| `app/indicators.py` | chỉ báo — chép nguyên bản nghiên cứu |
| `app/strategies.py` | sinh tín hiệu hai chiến lược |
| `app/executor.py` | hai lớp khoá, trần rủi ro, đặt lệnh giấy/thật |
| `app/runner.py` | một lượt chạy hằng ngày |
| `app/main.py` | web + lịch chạy nền |
| `app/static/index.html` | trang quản lý |
