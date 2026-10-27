# Thu carry trung hoà — chưa đáng mở chân spot

**Ngày chạy:** 27/10/2026 · **Dữ liệu:** funding thật `/fapi/v1/fundingRate`
của 623 mã USDT perp, 2021 → 2026-10-25.

Mua spot + bán perp cùng mã: hai chân triệt tiêu giá, lãi là funding chân bán
nhận được. Khác **carry cắt ngang** đã thử ở `xsmom-volnorm.md` (bán nhóm
funding cao, mua nhóm âm — đặt cược vào giá). Đây không phải câu hỏi "có tín
hiệu không" mà là "lợi suất bao nhiêu, ổn định tới đâu".

Nền lý thuyết: Schmeling, Schrimpf, Todorov (BIS WP 1087, *Management
Science*) — carry crypto có lúc 40–60%/năm, do nhu cầu đòn bẩy của nhà đầu
tư nhỏ và vốn kinh doanh chênh lệch giá bị giới hạn.

## Luật (đăng ký trước)

```
B0 thụ động : giữ liên tục BTC, ETH
B1 chủ động : mỗi 7 ngày, trong top 20 thanh khoản, giữ ≤ 5 mã funding
              7 ngày qua cao nhất và > 0; 1/5 mỗi mã; 7 sổ lệch ngày
phí         : 30 bps khứ hồi mỗi cặp (spot 2×10 + perp 2×5), chỉ cho mã đổi
vốn         : 1 USD danh nghĩa = 1 USD spot + 0,5 USD ký quỹ perp → chia 1,5
quyết       : đáng mở nếu ≥ 8%/năm trên vốn từ 2024-07 VÀ không năm đủ nào âm
```

8% là ngưỡng kinh doanh (≈ gấp đôi lãi phi rủi ro USD), không phải ngưỡng
thống kê.

## Kết quả

| năm | B0 BTC | B0 ETH | B1 thô | B1 phí | **B1 ròng** | B1 trên vốn |
|---|---|---|---|---|---|---|
| 2021 | 30,6% | 37,5% | 27,2% | 8,2% | 19,0% | 12,7% |
| 2022 | 4,2% | 0,8% | 2,8% | 6,7% | **−3,9%** | −2,6% |
| 2023 | 7,9% | 8,3% | 8,0% | 8,7% | −0,7% | −0,5% |
| 2024 | 12,0% | 13,0% | 16,4% | 8,1% | 8,3% | 5,5% |
| 2025 | 5,1% | 4,9% | 4,8% | 7,7% | **−3,0%** | −2,0% |
| 2026 | 2,5% | 1,7% | −0,8% | 8,5% | **−9,3%** | −6,2% |

B0 là % danh nghĩa, chưa chia 1,5. **Từ 2024-07: B1 −2,7%/năm, B0 BTC
+3,3%/năm trên vốn.** Trượt ngưỡng 8%, B1 âm 3 năm đủ → **chưa đáng mở**.

## Vì sao B1 thua cả bản thụ động

Funding **có tính bền** — tương quan 7 ngày qua → 7 ngày tới là **+0,61**
trên top 20:

```
funding 7 ngày qua   → 7 ngày tới (TB)
≤ 0                     −66,2 bps
0 – p80                  +6,8
p80 – p95               +35,6
> p95                   +82,8   (qua TB +134,1 — co lại một nửa)
```

Tức chọn mã theo funding quá khứ là **đúng**, nhưng phí đổi mã hằng tuần ăn
**~8%/năm**, lớn hơn phần thu thêm. Và từ 2025 chính phần thô đã co về
4,8% rồi −0,8%: chế độ funding hiện nay không còn trả carry.

**Carry không đa dạng hoá cho động lượng.** Năm carry tốt (2021, 2024) trùng
năm động lượng tốt; năm động lượng âm (2022, 2026) carry cũng thấp (B0
4,2% và 2,5%) hoặc âm (B1).

## Rủi ro chưa nằm trong con số

- **237/9.915 lần (2,4%)** mã đang giữ tăng > 40% trong một kỳ. Ở ký quỹ 2×,
  chân bán perp **bị thanh lý** nếu không nạp thêm giữa kỳ. Thu carry thật
  phải tái cân bằng ký quỹ hằng ngày.
- Bỏ qua chênh spot−perp (basis). Khi funding cao perp thường cao hơn spot,
  nên bỏ qua basis là ước lượng **thấp**.
- Giả định mọi mã đều có spot trên Binance — chưa kiểm.

## Khi nào nên xem lại

Không phải "thử biến thể khác" — mà theo dõi chế độ. Nếu funding BTC trượt
30 ngày quay lại cỡ 2021/2024 (> 12%/năm danh nghĩa), chạy lại script. B0
thụ động là bản đáng cân nhắc nhất khi đó: không tốn phí đổi mã.

Script: `scripts/carry_harvest.py`.
