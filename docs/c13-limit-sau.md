# PP5 · Lệnh mua limit sâu 2 ATR (C13)

Chiến lược này lấy từ tutorial bot của richmanbtc (Nhật, 指値 theo ATR) và lối "接针" (bắt râu nến) của trader Trung Quốc.
Bot chạy nó ở khung ngày. Nghiên cứu ngày 04/11/2026 (scratch `qs2/t2_hour.py`). Code ở `app/c13.py`.

**Từ 04/11/2026 C13 là chiến lược thứ 5 của bot** theo yêu cầu vận hành.
- Hệ số 1R là `ALLOC_C13` (mặc định **5** từ 04/11/2026 → 10 USD/lệnh), chỉnh ở tab «Cấu hình» → `alloc_c13`; đặt 0 là tắt. Ở hệ số 5, trần 1.000 USD treo/ngày chỉ đủ ~16 lệnh đầu bảng (replay: lãi ≈ 1.000 USD thay vì ≈ 2.900 không trần).
- Sổ giấy `C13_PAPER` (tab «Limit sâu (giấy)») vẫn chạy song song. Sổ này ghi mức khớp lý tưởng để đối chiếu với lệnh thật.

## Chạy trong bot

**Đầu lượt 00:05** (`c13.settle`):
- Đọc trạng thái các lệnh limit đặt ở lượt trước. Lệnh là GTD, sàn tự huỷ lúc 00:00 UTC.
- Phần đã khớp được ghi sổ thành vị thế `c13` và **đóng ngay trong lượt đó**, bằng lệnh thị trường reduceOnly, ở mức giá ≈ close ngày khớp.
- Ở chế độ giấy, lệnh được coi là khớp khi low ≤ limit, giá khớp = min(open, limit).

**Cuối lượt** (`c13.place`):
- Treo lệnh MUA LIMIT GTD cho nến kế tiếp ở mức `close − 2 × ATR14`, cỡ lệnh = 1R / (2 × ATR).
- Thứ tự đặt: theo hạng thanh khoản.
- **Bỏ qua** mã bot đang giữ vị thế (sàn chạy một chiều, lệnh mua khớp sẽ bù trừ vị thế bán) và mã bị chặn mua vì huỷ niêm yết.

**Trần:**
- tối đa `C13_MAX_ORDERS` lệnh (mặc định 50);
- tổng giá trị treo ≤ `C13_MAX_GROSS_USD` (mặc định 1.000);
- tổng giá trị treo ≤ trần phơi nhiễm của bot trừ phần đang mở;
- mỗi lệnh ≤ `MAX_ORDER_USD`.

Vị thế C13 không tính vào trần số lệnh / phơi nhiễm của lượt, vì nó đóng ngay trong lượt.

**Kiểm tra:** chạy lại `settle → đóng → place` trên lịch sử, chế độ giấy, trần 1.000 USD: 1.573 lệnh khớp, +0,184R mỗi lệnh, thắng 72%, +579 USD. Bản không trần cho +582 USD.

**Chưa có:**
- tab «Tính lịch sử» chưa mô phỏng C13;
- không có stop trong ngày (nghiên cứu cũng không có).

## Luật
- Sau mỗi nến ngày D đóng, với mỗi mã top 50 thanh khoản: đặt lệnh **mua limit** ở `L = close_D − 2 × ATR14_D`
  (ATR Wilder). Lệnh chỉ có hiệu lực trong nến D+1.
- Nếu low của D+1 ≤ L thì khớp ở min(open D+1, L) và **bán ở close D+1**. Không khớp thì hủy.
- 1R = 2 × ATR. Cỡ lệnh = `C13_R_USD` / 1R. Phí 10 bps khứ hồi; funding bỏ qua.
- Sổ ghi thêm bản **"ngân sách ngày"**: cả ngày chia nhau 1R. Lý do: ngày sập có thể khớp tới 50 lệnh cùng lúc.

## Backtest (04/2021 → 10/2026, top 50, 1R mỗi lệnh)
- 1.568 lệnh khớp trong 227 ngày. Mỗi lệnh lời +0,186R (+377 bps sau phí), thắng 72%.
- Vượt phép thử vào ngẫu nhiên: z 3,58 > ngưỡng Šidák 2,96.
- Dương cả 6/6 năm và 6/6 cách cắt nến ngày.
- Đặt limit càng sâu càng lời: 1,5 / 2 / 2,5 / 3 ATR cho +0,08 / +0,19 / +0,29 / +0,40R mỗi lệnh.
- **Rủi ro:**
  - 86% R đến từ 42 ngày cả thị trường sập.
  - Ngày 10/10/2025 lỗ −43,7R (50 lệnh khớp cùng lúc).
  - Nếu chạy cùng độ biến động với bot: tháng tệ nhất −43%.
- Chạy ở 1/4 độ biến động của bot: Sharpe cả bot 1,52 → 1,79, sụt lớn nhất không đổi.
- Kiểm tra code: chạy lại `c13.run_once` trên lịch sử ra 1.576 lệnh khớp, +0,185R mỗi lệnh, thắng 72% — khớp nghiên cứu.

## Xét lại
Sau khoảng 6 tháng: so R mỗi lệnh khớp với +0,19R của backtest, và xem có ngày sập nào lỗ quá lớn không.
Muốn chạy thật phải có thêm:
- trần số lệnh khớp mỗi ngày;
- ngân sách R theo ngày;
- cơ chế đặt và hủy khoảng 50 lệnh limit mỗi ngày trên sàn.
