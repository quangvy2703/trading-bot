# Lưới lại toàn bộ tham số, khung và chốt lời/cắt lỗ — 06/11/2026: GIỮ NGUYÊN

Người dùng yêu cầu grid search lại tham số của cả 6 phương pháp đang chạy và các
cách chốt lời/cắt lỗ, gồm cả khung thời gian. Windfall coi như đã deploy nên
nằm trong mốc. Lưới và luật quyết được viết trước khi chạy
(`crypto-p1/scripts/regrid/PLAN.md`).

## Cách đo

- **Mốc:** bot đang chạy cộng windfall (`app/methods_bt.json`). ALLOC: Động
  lượng 5, RSI(2) 8, TSVW 5, DSRM 5, C13 5, VSA 5; 1R = 2 USD; không áp trần.
  Kết quả mốc: lãi 16.336 USD, Sharpe 2,558, sụt 898 USD, 16/67 tháng âm.
- **Mỗi ô:** thay chuỗi lãi/lỗ của **một** phương pháp bằng chuỗi của ô đó,
  giữ nguyên các phương pháp còn lại, rồi đo trên lãi ngày của cả bot.
- **Tái lập mốc:** mỗi engine đều phải ra đúng chuỗi trong `methods_bt.json` ở ô
  mốc trước khi chạy lưới.
  - Động lượng + RSI(2): chênh 0.
  - TSVW, DSRM, C13, VSA: tương quan 1,0000, tổng chênh dưới 0,001%.
- **Thống kê:**
  - ΔSharpe so với mốc, bootstrap khối 30 ngày ghép cặp, 10.000 lượt.
  - Reality check max-over-grid trong từng lưới con.
  - Šidák qua 20 lưới con → α = 0,0026.
- **Luật quyết:** đổi tham số chỉ khi thoả cả ba điều kiện, ngược lại giữ:
  1. p của reality check < α;
  2. ô tốt nhất có ≥ 4/6 năm ΔSharpe ≥ 0;
  3. trung vị ΔSharpe của các ô láng giềng > 0.
- **Windfall** chỉ được bật trong lưới con windfall. Dữ liệu 5m/15m chỉ phủ các
  ngày giữ lệnh của mốc, nên các lưới khác của Động lượng được so trên nền không
  windfall, rồi cộng phần windfall của mốc như một hằng số.

## Kết quả: không lưới con nào qua luật

| Lưới con | Số ô | p reality check | Ô tốt nhất | ΔSharpe (KTC 99,74%) | Năm | Láng giềng | Hạng ô đang chạy |
|---|---|---|---|---|---|---|---|
| Động lượng: vào lệnh (topn × lookback × giữ × MA) | 81 | 0,850 | top 20, lookback 14, giữ 3, MA 30 | +0,237 [−0,70; +1,25] | 3/6 | +0,076 | 17 |
| Động lượng: Kase | 10 | 1,000 | **đang chạy** (2,2/30) | — | | | 1 |
| Động lượng: dừng an toàn | 4 | 0,734 | 6R | +0,015 [−0,10; +0,14] | 3/6 | −0,004 | 2 |
| Động lượng: chốt lời C4 | 18 | 0,792 | F08 x 0,1 | +0,028 [−0,12; +0,18] | 4/6 | −0,009 | 3 |
| Động lượng: windfall | 21 | 0,545 | 5m, k 35, mở lại | +0,069 [−0,00; +0,22] | **6/6** | +0,042 | 9 |
| RSI(2): vào lệnh (vào × ra × topn × lớp) | 81 | 0,973 | ra 60, top 20 | +0,007 [−0,06; +0,08] | 4/6 | +0,001 | 5 |
| RSI(2): cắt lỗ (ATR × HVN) | 6 | 0,739 | 4 ATR + HVN | +0,001 | 5/6 | −0,022 | 2 |
| TSVW: vào lệnh | 81 | 0,970 | N 30 | +0,018 | 3/6 | −0,024 | 5 |
| TSVW: chốt lời / cắt lỗ | 15 | 0,773 | chốt 3R | +0,027 | 5/6 | +0,011 | 5 |
| TSVW: khung / số mã | 7 | 0,488 | top 100 (1D) | +0,064 | 5/6 | — | 2 |
| DSRM: vào lệnh | 108 | 0,760 | W 4, chốt 2R | +0,067 [−0,07; +0,18] | 5/6 | +0,017 | 27 |
| DSRM: chốt lời | 5 | 0,622 | chốt 2R | +0,035 | 5/6 | +0,008 | 3 |
| DSRM: khung / số mã | 7 | 0,452 | top 100 (1D) | +0,103 [−0,12; +0,32] | 5/6 | — | 3 |
| C13: vào lệnh (k × ATR × topn) | 54 | 0,873 | k 2,5, ATR 7, top 100 | +0,102 [−0,16; +0,35] | 5/6 | +0,030 | 11 |
| C13: thoát | 3 | 1,000 | **đang chạy** (close ngày khớp) | — | | | 1 |
| C13: khung | 5 | 0,599 | 12H | +0,065 [−0,63; +0,60] | 5/6 | — | 3 |
| VSA: vào lệnh | 9 | 1,000 | **đang chạy** | — | | | 1 |
| VSA: giữ × khung | 25 | 1,000 | **đang chạy** (4H, giữ 3) | — | | | 1 |
| VSA: số mã | 3 | 1,000 | **đang chạy** (top 50) | — | | | 1 |

Bảng đầy đủ từng ô nằm ở `crypto-p1/scripts/regrid/tables/score_*.txt`. Cột
"Hạng ô đang chạy" là hạng của tham số hiện tại trong lưới con đó, xếp theo
ΔSharpe.

## Đọc kết quả

- **Giữ nguyên toàn bộ tham số, khung và cách chốt lời/cắt lỗ.** Không lưới
  con nào có p reality check gần α. Kiểm tra phụ bằng reality check chuẩn hoá
  (max t, kiểu Hansen SPA; không nằm trong luật đăng ký) cũng không lưới nào
  dưới 0,05.
- **Ứng viên duy nhất đáng theo dõi là windfall 5m, k 30–35, có mở lại.**
  - ΔSharpe +0,06 / +0,07, dương ở 6/6 năm. Riêng ô k 30 có KTC [+0,006; +0,159]
    không chứa 0.
  - Sau khi tính việc đã chọn ô tốt nhất trong 21 ô: p 0,545 (luật đăng ký),
    0,080 (bản chuẩn hoá). Chưa đủ để đổi.
  - Nghiên cứu cũ ghi rằng hiệu quả của bản 5m yếu đi trong 2025–26. Nên chạy
    sổ giấy song song với bản 15m trước khi đổi.
- **Các lưới đang được dùng đều đã nằm ở đỉnh của chính chúng:** Kase, VSA, C13
  thoát lệnh. Đây là dấu hiệu tham số đã được chọn trên cùng dữ liệu này, không
  phải bằng chứng là chúng tốt ngoài mẫu.
- **Động lượng giữ 3 ngày** có Sharpe cao hơn nhưng lãi thấp hơn khoảng 2.000
  USD, sụt nhỏ hơn. KTC rộng ±1, vì đổi lịch tái cân bằng làm đổi toàn bộ chuỗi
  của phương pháp lớn nhất bot.
- **Top 100 cho DSRM/TSVW/C13** thêm lãi (+1.000…+1.500 USD), nhưng chủ yếu là
  thêm lệnh, tức thêm phơi nhiễm, và KTC chứa 0. Kết luận này giống bài học cũ
  với số mã của Động lượng.
- **Bỏ một luật đang chạy luôn làm kém đi,** nên các luật này đáng giữ:
  - bỏ Kase: ΔSh −0,27;
  - bỏ C4: −0,13 (KTC loại 0);
  - bỏ windfall: −0,10 (KTC loại 0);
  - bỏ stop HVN: −0,05.

## Kế toán

Tổng 543 ô:
- Động lượng 134 → **1.572**;
- RSI(2) 87 → **≈ 565**;
- TSVW / DSRM 223;
- C13 62;
- VSA 37.

## Khác biệt nhỏ cần biết

- **VSA:** hệ số KL/biên độ chỉ áp cho nến "đẩy qua vùng cung"; dấu hiệu mạnh
  giữ ngưỡng 1,5×.
- **TSVW/DSRM khung "giữ thời gian":** nhân cả chu kỳ chỉ báo (ATR, Stoch, RSI,
  MACD) và thời gian giữ.
- **Top 100 trên khung 4H:** thiếu dữ liệu cho khoảng 1–8% mã.
- **Động lượng, các ô top 30:** một số mã mới không có dữ liệu windfall; không
  ảnh hưởng, vì windfall chỉ bật ở lưới con riêng.
