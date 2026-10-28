# Bán khống perp mới niêm yết — giá rơi thật, chiến lược không

**Ngày chạy:** 27/10/2026 · **Dữ liệu:** nến 1D + funding thật, mọi perp USDT
của Binance từng tồn tại, kể cả đã huỷ niêm yết · **615 sự kiện niêm yết**
từ 2020-09-23 đến 2026-10-01 · script `scripts/listing_short.py`

## Kết luận một dòng

**70% mã mới niêm yết rơi trong 30 ngày đầu, trung vị −21%** — nhưng bán khống
cả rổ lời **−116 bps/lệnh**, vì vài cú bơm ×5 đến ×34 ăn hết. Trượt luật đăng
ký trước → **LOẠI**.

## Luật (đăng ký trước, trong docstring script)

```
sự kiện : perp crypto có nến 1D đầu tiên sau 2020-09-20
vào     : BÁN ở open nến 1 (ngày đầy đủ đầu tiên; nến 0 là ngày niêm yết, thiếu)
thoát   : close nến 30 (giữ 30 ngày)
phí     : 10 bps/lệnh · funding thật, chân bán NHẬN khi rate > 0
rào     : bản phụ + long BTC cùng danh nghĩa (thêm 10 bps)
chốt nếu: (1) nửa dò (niêm yết < 2024-07) TB ròng > 0
          (2) nửa kiểm (≥ 2024-07) KTC95 loại 0 phía dương
              — bootstrap theo THÁNG niêm yết
          (3) bản rào BTC cũng dương ở cả hai nửa
```

Lưới 3 độ trễ × 5 chân trời = 15 ô chỉ để mô tả, không dùng để chọn.

## Giá đi về đâu sau niêm yết

So với open nến 1, chưa phí:

| Ngày | n | TB | **Trung vị** | % dưới giá vào | BTC cùng kỳ |
|---|---|---|---|---|---|
| 1 | 615 | −0,8% | −4,4% | 62,4% | +0,1% |
| 7 | 615 | −2,6% | −12,1% | 68,0% | +1,0% |
| 14 | 615 | −1,1% | −15,5% | 68,9% | +2,0% |
| **30** | 614 | **−0,7%** | **−20,6%** | **70,0%** | +4,7% |
| 60 | 611 | +3,9% | −27,6% | 73,8% | +7,9% |
| 90 | 608 | **+29,8%** | −38,4% | 75,2% | +12,6% |
| 180 | 580 | +13,2% | **−50,1%** | 76,7% | +21,2% |

Trung vị rơi đều, không dừng: sau nửa năm, **mã điển hình mất một nửa**, ba
phần tư nằm dưới giá vào. Nhưng **trung bình đi ngang rồi dương** — đó là hình
dạng của vé số: đa số mất, rất ít trúng lớn, và phần trúng đủ bù.

## Ô chính: k = 1, giữ 30 ngày

| | n | TB ròng | Trung vị | Thắng | KTC95 |
|---|---|---|---|---|---|
| toàn mẫu · bán trần | 614 | **−116** | +1.901 | 69,7% | [−1.312 ; +969] |
| toàn mẫu · rào BTC | 614 | +345 | +2.350 | 73,9% | [−877 ; +1.347] |
| nửa dò · bán trần | 238 | **−101** | +1.432 | 67,6% | [−1.557 ; +1.208] |
| nửa dò · rào BTC | 238 | +862 | +2.163 | 78,2% | [−247 ; +1.911] |
| nửa kiểm · bán trần | 376 | **−126** | +2.445 | 71,0% | [−1.983 ; +1.377] |
| nửa kiểm · rào BTC | 376 | +18 | +2.433 | 71,3% | [−1.875 ; +1.408] |

(bps/lệnh). **Trượt (1) và (2)**, (3) chỉ qua sát nút ở nửa kiểm (+18).

Đuôi trái của lệnh bán: p5 −107% · p1 −294% · **33/614 lệnh lỗ quá 100%**
(giá ×2 trong 30 ngày) · tệ nhất COAI **−3.260%** (giá ×33,6), GMT −581%,
BEAT −471%, NEIRO −446%. Lệnh thắng nhiều nhất chỉ được +96% (giá về gần 0).
Lời bị chặn trên ở 100%, lỗ thì không — **bán vé số là bán quyền chọn mua**.

Theo năm niêm yết, bán trần âm 5/7 năm dù trung vị dương 6/7 năm.

## Cắt lỗ — nhìn SAU khi có số, không dùng để chốt

| Stop | TB | Lệnh tệ nhất | nửa dò | nửa kiểm | KTC nửa kiểm |
|---|---|---|---|---|---|
| không | −116 | −326.006 | −101 | −126 | [−2.019 ; +1.390] |
| +100% | +181 | −12.277 | +56 | +261 | [−563 ; +1.023] |
| **+50%** | **+348** | −8.684 | +108 | +499 | [−163 ; +1.112] |
| +30% | +291 | −6.432 | +122 | +398 | [−100 ; +880] |

Khớp ở `max(stop, open)` trên nến ngày. Stop biến âm thành dương ở cả hai nửa,
nhưng **không ô nào có KTC loại 0**, và ba mức stop được chọn sau khi đã thấy
đuôi — đây là ứng viên cho một lần thử mới, không phải kết quả. Lệnh tệ nhất
vẫn −87% vì giá **nhảy qua** stop lúc mở cửa; trên thực tế mã mới có râu nến
và trượt giá lúc ép còn tệ hơn mô hình nến ngày.

## Dữ liệu — những gì đã kiểm

- **Mã chết sớm có mặt.** `uni1d` bỏ mã < 200 nến; `scripts/listing_fetch.py`
  tải bổ sung 172 mã vào `reports/.cache/listing1d/`. Kiểm: không mã nào bị
  huỷ trong 30 ngày đầu (ngắn nhất 31 nến), nên với ô chính không có thiên
  lệch sống sót.
- **Perp TradFi bị loại** (cổ phiếu, hàng hoá, pre-market — 236 mã theo
  `exchangeInfo`, lưu `_noncoin.json`). `is_crypto()` không đủ: perp TradFi
  2026 giao dịch cả cuối tuần.
- **Đổi tên không tính là niêm yết:** POL, S, RENDER, A, SKY, 1000BTTC (danh
  sách tay, đã kiểm ngày mã cũ dừng 1–10 ngày trước). Bản đầu dùng luật tự
  động "mã chết trong 0–5 ngày trước" và loại nhầm 186 mã (ARB, 0G,
  FARTCOIN…) — trùng ngày ngẫu nhiên; đã bỏ trước khi đọc kết quả cuối.

## Kế toán phép thử

1 ô chính, quyết bằng nửa kiểm riêng. Mẫu sự kiện (niêm yết) khác mẫu danh mục
của động lượng, nhưng cùng khoảng lịch. Bảng stop là **nhìn sau** — muốn dùng
phải chờ dữ liệu niêm yết sau 2026-10 (dự kiến ~100 sự kiện/năm).

## Tệp

- `scripts/listing_fetch.py` — tải mã ngắn + `_onboard.json`
- `scripts/listing_short.py` — toàn bộ bảng trên, luật trong docstring
