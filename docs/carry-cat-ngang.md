# Carry funding cắt ngang, đợt 2 — 06/11/2026: LOẠI

Người dùng yêu cầu: "Carry funding: làm thêm nhé". Các lần thử trước:
- `xsmom-volnorm.md`, họ C: 1/6 ô qua.
- `gh_factor_mom`: CARRY dương ở 6/6 ô, Sharpe 0,5–1,0, mạnh nhất ở top 100.
- `carry-trung-hoa.md`: carry trung hoà spot–perp không đáng mở.

Lần này carry được đo **như một phương pháp của bot**: chuỗi lãi/lỗ theo ngày,
tính bằng R, ghép vào bot đang chạy. Luật viết trước trong
`scripts/carry_xs2.py`.

## Cách làm

- **Dữ liệu:** perp 1D cắt 00h, gồm cả mã đã huỷ niêm yết, funding thật
  (`screen_families.build`).
- **Chọn mã:** ngày i, trong top N thanh khoản, xếp theo funding trung bình L
  ngày. Có ba kiểu:
  - LS: bán k mã funding cao nhất và mua k mã funding thấp nhất;
  - S: chỉ chân bán;
  - L: chỉ chân mua.
- **Giữ lệnh:** vào ở open i+1, giữ H ngày. Có H sổ lệch ngày nhau, giống Động
  lượng.
- **Cỡ lệnh:** mỗi vị thế 1R = 1 ÷ (σ30 · √H), chia đều cho H sổ.
- **Phí:** 10 bps khứ hồi mỗi vị thế mỗi kỳ.
- **Lưới 288 ô:** kiểu {LS, S, L} × top N {20, 50, 100} × L {1, 3, 7, 30} ngày ×
  H {1, 3, 7, 14} ngày × k {2, 5}.
- **Mốc:** bot đang chạy + windfall + Impulse MACD bán ALLOC 2. Lãi 17.350 USD,
  Sharpe 2,558. Carry được thêm vào với ALLOC 2.
- **Luật quyết, cần cả bốn:**
  1. reality check max-over-grid trên ΔSharpe của bot, p < 0,05;
  2. ít nhất 4/6 năm tốt hơn;
  3. các ô láng giềng tốt hơn;
  4. phần lãi từ funding dương ở ít nhất 4/6 năm.

## Kết quả

**Reality check p = 0,559; bản chuẩn hoá p = 0,232 → LOẠI.**

| Ô | ΔSharpe bot (KTC 95%) | Năm | Sharpe riêng | R tổng | R từ funding | Tương quan với Động lượng |
|---|---|---|---|---|---|---|
| Tốt nhất: chỉ MUA, top 20, L 3, H 3, k 5 | +0,118 [+0,005; +0,230] | 5/6 | 0,54 | 144 | 38 | −0,02 |
| LS, top 20, L 3, H 3, k 5 | +0,047 [−0,013; +0,110] | 4/6 | **1,14** | 156 | 73 | +0,19 |
| LS, top 50, L 7, H 7, k 2 | +0,010 | 5/6 | 0,59 | 34 | 51 | +0,08 |

Toàn lưới:
- 52% số ô làm Sharpe bot tăng; trung bình gần 0.
- 77% số ô có Sharpe riêng > 0.
- **100% số ô có phần lãi từ funding > 0.**

Theo kiểu:

| Kiểu | ΔSharpe trung bình | Sharpe riêng trung bình |
|---|---|---|
| L (chỉ mua) | +0,032 | 0,18 |
| LS | −0,006 | 0,46 |
| S (chỉ bán) | −0,063 | 0,12 |

## Đọc kết quả

- **Bản thân funding thì luôn có lãi**, ở mọi ô và gần như mọi năm. Ví dụ ô LS
  top 100, L 7, H 7: thu 10–29R mỗi năm. **Nhưng phần lãi/lỗ do giá lớn hơn và
  thất thường hơn phần funding.** Mã funding cao thường là mã đang được mua mạnh
  và vẫn tiếp tục tăng, nên chân bán lỗ giá.
- **Ô tốt nhất thực chất không phải carry.** Kiểu chỉ MUA nhóm funding âm nhất
  phần lớn là cược giá bật lên khi phe bán khống bị ép (2022: −96R, 2023/2024:
  +82/+84R). Phần funding chỉ 38/144R.
- **Kiểu LS có Sharpe riêng cao nhất (1,14)** nhưng tương quan +0,19 với Động
  lượng: bán mã funding cao trùng một phần với việc ngược chân mua của Động
  lượng. Vì vậy ghép vào bot chỉ được +0,05, KTC chứa 0.
- **Kết luận giống đợt carry trung hoà:** funding là dòng tiền có thật nhưng nhỏ
  so với rủi ro giá. Muốn thu sạch thì phải phòng hộ giá, tức là carry trung hoà
  spot–perp, mà bản đó đã bị phí đổi mã ăn hết từ 2025.

## Kế toán

+288 ô nhóm cắt ngang → **1.860**. Bảng đủ ở `crypto-p1/reports/carry_xs2.txt`;
script `scripts/carry_xs2.py` và `scripts/carry_xs2_score.py`.
