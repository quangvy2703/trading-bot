# PP6 · VSA 4H — "đẩy qua vùng cung" rồi nến giảm khối lượng thấp

Nguồn: Tom Williams, *Master the Markets* (TradeGuider, 2009), phương pháp
Volume Spread Analysis (VSA). Nghiên cứu ngày 02/11/2026, script trong
`../scripts/`: `gh_vsa.py` (lưới), `gh_vsa_verify.py` (độ bền),
`gh_vsa_corr.py` (tương quan), `gh_vsa_rs.py` (chọn mã mạnh hơn chỉ số).

**Trạng thái: PP6 của bot từ 04/11/2026** (hệ số `alloc_vsa`, mặc định 5;
0 là tắt) — đưa vào theo yêu cầu vận hành, **trước** mốc «≥ 300 lệnh giấy» ở
cuối trang. Ô này được chọn *sau khi* nhìn 324 ô, nên sổ giấy (tab «VSA 4H»)
vẫn chạy song song làm phép thử ngoài mẫu.

## Luật

Khối lượng và biên độ so với **trung bình 30 nến trước**. "Thấp" theo đúng
sách (tr. 17): nhỏ hơn **cả hai** nến trước. Mỗi nến 4H vừa đóng, với mỗi mã
top 50 thanh khoản (trung vị giá trị giao dịch 30 ngày, ngày đã đóng):

1. **Có nến đẩy qua vùng cung trong 10 nến trước** (sách tr. 35, 63): nến
   tăng, biên độ > 1,5× TB, khối lượng > 1,5× TB, đóng ở 1/3 trên, close vượt
   đỉnh 20 nến.
2. **Có sức mạnh ở nền trong 20 nến trước** (tr. 108, "test chỉ là tín hiệu
   mua khi có sức mạnh ở nền"): nến giảm khối lượng > 1,5× TB đóng từ giữa
   trở lên, hoặc nến rộng chạm đáy 20 nến, khối lượng cao, đóng ≥ 0,6.
3. **Nến vừa đóng là nến giảm, khối lượng thấp** (không có áp lực bán).

→ Mua ở **open nến kế**, bán ở **close nến thứ 3** (giữ 12 giờ). Một lệnh một
mã một lúc. Phí 10 bps khứ hồi + funding thật. Không stop.

App chạy 00:02, 04:02, … UTC. Lượt chạy trễ hơn 15 phút sau open nến vào thì
ghi **"bỏ lỡ"** và không vào (giá open đã qua, vào muộn không còn là phép thử
của backtest).

## Kết quả backtest (top 50, 2021-04 → 2026-10)

| | |
|---|---|
| Lệnh | 3.594 (~1,8/ngày; đồng thời TB 2,8, p95 9, tối đa 31) |
| Lời ròng TB | **+38,7 bps/lệnh** (null vào ngẫu nhiên −7,7) |
| Trung vị / thắng | −6,9 bps / 49% — lời nằm ở đuôi phải |
| Theo năm | 21 +115 · 22 +12 · 23 +48 · 24 +29 · **25 −15** · 26 +35 |
| Bỏ 10 lệnh lời nhất | +25,5 · bỏ BTC/ETH +40,9 |

Độ bền: 4/4 cách lệch nến 4H (0/1/2/3 giờ) dương, z 1,4–3,6; top 10 / 20 /
50 đều dương; nửa 2021–23 +69 (z 3,7), nửa 2024–26 **+26 (z 1,5)** — yếu đi.

Trong lưới 324 ô (12 họ VSA × nền × cách ra × 1D/4H/1H), không ô nào đạt
luật Šidák; ô này có z 3,72 so với ngưỡng 3,78. Hai ô khác qua FDR đã bị
loại khi kiểm độ bền: *stopping volume 1D* (+406 bps nhưng chỉ 3/6 mốc cắt
ngày dương — mốc 8h, 12h âm) và *no demand 1D bán* (z TB các mốc 1,8).

## Với danh mục đang chạy

Tương quan PUSH–động lượng: ngày +0,08, tuần +0,19, tháng +0,39; với RSI(2)
+0,04 / +0,09 / +0,26. Ghép theo nghịch đảo biến động: Sharpe động lượng
1,36 → 1,81 (chênh +0,45, KTC95 [−0,07 ; +0,93]; 2025 âm); cả ba chiến lược
1,59 → 1,97 (+0,38, KTC95 [−0,06 ; +0,76]). Có ích nhưng chưa chắc.

## Chạy trong bot (PP6)

- Lịch riêng mỗi 4 giờ (00:02, 04:02, … UTC), chung lịch với sổ giấy, trong
  khoá của lượt ngày (không chạy chồng lượt 00:05 hay «ép lệnh»).
- **Mở:** tín hiệu ở nến vừa đóng, lượt chạy trong 15 phút sau open nến vào →
  MUA thị trường (chạy thật) / ghi ở open nến (sổ bot giấy). Trễ hơn → «bỏ lỡ».
- **Đóng:** nến thứ 3 đã đóng → BÁN thị trường reduceOnly (≈ close nến đó).
  Lượt ngày giữ nguyên vị thế PP6; nếu lượt ngày mở chiều BÁN cùng mã (sàn
  một chiều) thì vị thế PP6 bị đóng sớm («đóng để mở ngược chiều»).
- **Cỡ lệnh:** không có stop nên 1R quy ước = giá đi `VSA_R_FRAC` (10%), cỡ
  lệnh = 1R / 0,10 → 5 × 2 USD / 0,10 = **100 USD**, đúng cỡ sổ giấy; rủi ro
  ngày tương đương PP3/PP4 ở hệ số 5 (độ lệch chuẩn ngày ≈ 10 USD).
- **Dừng an toàn trên sàn:** SAFETY_R × 1R = giá −30% (chỉ chống thảm hoạ).
- **Bỏ mã:** PP6 đang giữ, bot đang giữ chiều BÁN mã đó, thông báo huỷ niêm yết.
- **Trần:** `VSA_MAX_OPEN` = 20 lệnh cùng lúc (backtest p95 9, tối đa 31) + các
  trần chung (trần lệnh, tổng phơi nhiễm, số lệnh mở).
- Lãi/lỗ chốt giữa hai lượt ngày cộng vào vốn ở lượt ngày kế tiếp.
- Tab «Tính lịch sử» không mô phỏng PP6.

## Mốc đánh giá lại

Sau **≥ 300 lệnh** (~6 tháng, sổ giấy và sổ bot): TB bps/lệnh dương và KTC95
không thấp hơn hẳn +38,7 của backtest; số lệnh/ngày và tỉ lệ «bỏ lỡ» khớp kỳ
vọng. Không đạt → hạ `alloc_vsa` về 0.
