# Dữ liệu ngoài giá perp — ba nguồn, một manh mối

**Ngày chạy:** 27/10/2026 · **Mẫu:** 2021-01-01 → 2026-10 · script
`scripts/alt_factors.py` (luật trong docstring, viết trước khi chạy),
dữ liệu `scripts/alt_fetch.py`

| Nguồn (miễn phí, phủ 2021–2026) | Tín hiệu | Kết quả |
|---|---|---|
| DefiLlama TVL theo giao thức | S1 · Δ30 log TVL → mua | **Loại** — vũ trụ quá nhỏ (trung vị 24 mã), chỉ dùng được từ 2023 |
| Binance spot + perp | S2 · khối lượng perp / spot cao → bán | **Loại theo luật, sát nút** — +62 bps/kỳ, KTC98 [−2 ; +135] |
| DefiLlama tổng cung stablecoin | S3 · Δ30 cao → thị trường tăng | **Loại** — dấu sai, trạng thái kéo dài nhiều tháng nên không phân giải được |

Không lấy được miễn phí: lịch mở khoá token (DefiLlama emissions là gói trả
tiền), lịch sử vốn hoá (CoinGecko miễn phí chỉ 365 ngày), OI / tỉ lệ
long-short (chỉ có từ 2021-12, 54 mã — xem `dong-tien-cuong-buc.md`).

## Luật chung (đăng ký trước)

S1, S2: mỗi ngày mua 1/5 điểm tốt nhất, bán 1/5 tệ nhất, chia đều, vào open
hôm sau, giữ 7 ngày, phí 20 bps cho cả cặp, **chưa tính funding**. Chốt khi
đủ cả bốn, trên toàn bộ thời gian:

1. KTC 98,3% (Bonferroni 3 tín hiệu, bootstrap block 30 ngày) loại 0 đúng chiều
2. ≥ 4/6 năm cùng chiều
3. hai lân cận cửa sổ (14, 60) cùng chiều, ≥ nửa độ lớn
4. phần dư sau khi hồi quy lên nhân tố động lượng vẫn đúng chiều

## S2 — tỉ lệ đầu cơ perp/spot

`log(Σ30 khối lượng USD perp / Σ30 khối lượng USD spot Binance)`, vũ trụ top
100 thanh khoản có cặp spot (475/676 mã có spot).

```
TB +62,0 bps/kỳ · KTC98 [−2,1 ; +134,6] · 2.117 ngày
năm   2021 +6 · 2022 −45 · 2023 −12 · 2024 +139 · 2025 +157 · 2026 +143
lân cận 14n +47,4 · 60n +56,3
tương quan với động lượng −0,10 · phần dư +61,0 KTC98 [−2,7 ; +134,1]
```

Trượt (1) và (4) trong gang tấc, qua (2) và (3). **Loại theo luật.**

### Mổ xẻ — nhìn sau, chỉ để mô tả

- **Hai chân đóng góp đều:** mã đầu cơ thấp hơn vũ trụ +42 bps, mã đầu cơ cao
  kém vũ trụ −40 bps. Không phải chuyện một chân.
- **Không phải quy mô.** Mã spot mạnh thường là coin lớn, nên nghi vấn đầu tiên
  là "coin lớn thắng altcoin 2024–2026". Kiểm soát bằng hồi quy lên nhân tố
  quy mô: phần dư +75,6 KTC95 [+26 ; +130]. Sắp xếp kép (xếp đầu cơ **trong**
  từng nửa quy mô): +78,4 KTC95 [+27 ; +139]. Nhân tố quy mô trong top 100 tự
  nó còn âm (−64,8).
- **Không phải động lượng:** tương quan −0,10, tức gần như độc lập — đúng
  loại thứ danh mục đang thiếu.
- **Phụ thuộc vũ trụ:**

| vũ trụ | 1/5 | 1/3 | theo năm (1/3) |
|---|---|---|---|
| top 50 | +88 [+28 ; +166] | +65 [+16 ; +126] | +32 +29 +9 +33 +148 +158 |
| **top 100 (luật)** | **+62** [+8 ; +119] | +37 [−2 ; +86] | −15 −8 +16 +63 +87 +90 |
| top 200 | +10 [−34 ; +63] | +3 [−30 ; +47] | −5 −36 −25 +34 +2 +62 |

(bps/kỳ, KTC95). Mạnh dần khi vũ trụ **hẹp lại**, mất ở top 200.

**Vì sao chưa tin:** gần như toàn bộ lợi thế nằm ở 2024–2026; 2022–2023 bằng
0 hoặc âm ở bản luật. Đó đúng là hình dạng mà "toàn bộ thời gian, không phải
may mắn" muốn loại. Top 50 · 1/3 dương cả 6 năm, nhưng là ô được chọn sau
khi thấy 6 ô.

**Cách kiểm sạch duy nhất còn lại:** chạy tiến (paper) — ghi tín hiệu mỗi
ngày từ giờ, không cho chạm tiền, sau 6–12 tháng mới đánh giá. Hoặc đo cùng
tín hiệu bằng khối lượng của sàn khác (Bybit/OKX) — đo độc lập phần tín
hiệu, dù lợi suất vẫn là cùng một chuỗi.

## S1 — TVL

214/676 perp nối được giao thức (gom theo ký hiệu, bỏ CEX/cầu nối/chuỗi, bỏ
ký hiệu mơ hồ). TVL chỉ dùng từ ngày DefiLlama bắt đầu theo dõi + 30 ngày
(trước đó là số điền ngược). Còn trung vị **24 mã/ngày** ở TVL ≥ 10 triệu,
chỉ 1.063/2.126 ngày đủ 25 mã → chủ yếu 2023 trở đi.

```
TB −10,6 · KTC98 [−161,5 ; +141,5] · năm + 1/4 · lân cận +74 / +64
```

Không có gì, và khoảng tin cậy rộng ±150 bps — mẫu không đủ để thấy bất kỳ
hiệu ứng nào cỡ hợp lý. Ký hiệu trùng (vài token khác tên cùng ký hiệu với
giao thức) làm thêm nhiễu.

## S3 — stablecoin

```
Δ30 cao (tam phân vị trên của quá khứ)  : TB 7 ngày −192 bps (216 ngày)
Δ30 thấp                                : −156 (814 ngày)
giữa                                    : +108
cao − thấp −37 · KTC98 [−353 ; +348] · lân cận +6 / −160
```

Sai chiều dự đoán, và chỉ 2025 có đủ cả hai trạng thái. Cung stablecoin đi
theo chu kỳ nhiều tháng (tăng 2021, giảm 2022–23, tăng 2024–25) nên một chuỗi
thời gian 6 năm chỉ có vài "lần quan sát" thật.

## Kiểm độc lập S2 bằng khối lượng Bybit — KHÔNG xác nhận

Cùng luật S2, chỉ đổi nguồn điểm: `log(Σ30 turnover perp Bybit / Σ30
turnover spot Bybit)`, lợi suất vẫn là perp Binance. Đăng ký trước một phép
thử xác nhận (α 5%): KTC95 > 0, TB 2022+2023 > 0, ≥ 4 năm dương, lân cận
cùng chiều. Script `scripts/alt_bybit.py`, dữ liệu `scripts/bybit_fetch.py`
(346 mã có cả spot lẫn perp Bybit; spot Bybit mở 2021-07, đủ 25 mã từ
2021-12).

| | TB bps/kỳ | KTC95 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| **Bybit perp/spot** | **+1,4** | [−49 ; +54] | +30 | −19 | −19 | −18 | +50 |
| lân cận 14 / 60 | +8,6 / +11,8 | chứa 0 | | | | | |
| Binance trên **cùng** tập mã-ngày | +53,3 | [−2 ; +107] | +12 | +66 | +39 | +98 | +69 |
| Binance toàn top 100 (bản cũ) | +62,0 | [+9 ; +121] | −45 | −12 | +139 | +157 | +143 |

Trượt (1) và (3). Trên cùng tập mã và ngày, điểm Binance vẫn cho +53 còn
điểm Bybit cho **0** — nên không phải do vũ trụ hẹp lại, mà do **thước đo**.
Tương quan hạng giữa hai điểm chỉ +0,35.

Đọc lại: thứ dự báo được không phải "đầu cơ đòn bẩy" nói chung (nếu vậy sàn
nào đo cũng phải thấy), mà là **thanh khoản spot riêng trên Binance** so với
perp Binance. Giả thuyết còn lại — chưa kiểm — là nó đo *Binance có coi
trọng mã này ở spot không* (mã chỉ có perp hoặc spot mỏng trên Binance là mã
yếu hơn). Đó là một tín hiệu khác, phải đăng ký lại từ đầu, và vẫn vướng
đúng điểm yếu cũ: lợi thế bản gốc tập trung ở 2024–2026.

**Kết luận: S2 dừng ở đây.** Không đưa vào bot, không theo dõi tiến.

## Kế toán phép thử

+3 ô (S1, S2, S3), Bonferroni trong đợt, +1 ô xác nhận Bybit. Bảng mổ xẻ S2
là nhìn sau.
