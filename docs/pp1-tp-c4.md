# PP1 · chốt lời lệnh bán mỗi giờ (C4 = F08 + P16)

Vào bot 05/11/2026 (`app/pp1tp.py`, công tắc `xsmom_tp` / `XSMOM_TP`, mặc định bật). Áp cho chế độ đang chạy: sổ giấy,
hoặc lệnh thật khi đã bật `live_armed`.

## Luật
Chỉ lệnh **BÁN** của PP1. Mỗi giờ, phút 1 UTC, kiểm ở giá đóng của nến 1H vừa chốt. Lãi u = side × (giá / giá vào − 1)
÷ (r_usd / notional), đơn vị R.

| Nhánh | Điều kiện | Tham số |
|---|---|---|
| **F08** | u ≥ 0,5R **và** q ≤ 0,8. s = KL spot ÷ (KL spot + KL perp), cộng 3 ngày UTC gần nhất đã đóng; q = s ÷ trung vị 60 ngày (≥ 30 ngày có số liệu) | `XSMOM_TP_F08_X` 0,2 · `XSMOM_TP_F08_M` 0,5 |
| **P16** | đang ở ngày giữ thứ 4 (ngày UTC chứa giờ vào + 3) **và** u ≥ 1R | `XSMOM_TP_P16_H` 4 · `XSMOM_TP_P16_M` 1,0 |

- Thoả một trong hai nhánh thì đóng **toàn bộ** lệnh ở giá thị trường, xấp xỉ giá mở nến 1H kế tiếp.
  - Lệnh đi qua `executor` như lượt ngày: sổ giấy dùng giá hiện tại; chạy thật dùng limit/market reduceOnly.
- Chỗ trống để nguyên tới lần tái cân bằng của sổ đó.
- Ở nến 00:00 UTC, bỏ qua sổ sẽ tái cân bằng lúc 00:05.
- Khối lượng spot lấy từ nến 1D của `api.binance.com`, cặp cùng tên hoặc bỏ tiền tố 1000 / 1000000 / 1M. Mã không có cặp
  spot thì nhánh F08 không chạy.
- KL perp = close × volume nến 1D của hợp đồng.
- Lãi/lỗ đã chốt cộng vào `tp_realised:<mode>`, lượt ngày kế tiếp cộng vào vốn (giống PP6).
- Trạng thái lượt gần nhất lưu ở kv `pp1tp_last`. Các lệnh đóng được ghi vào log với lý do «chốt lời F08 / P16».

## Bằng chứng
Engine B10+K (Kase + BSADF + stop 3R trên sàn), bot 6 PP ở hệ số 5/8/5/5/5/5, **không trần**, 07/04/2021 → 25/10/2026.

| | Mốc | C4 |
|---|---|---|
| Lãi | 15.150 | 15.641 (+491) |
| Sharpe | 2,335 | 2,455 |
| Sụt lớn nhất | 911 | 900 |
| Tháng âm | 17/67 | 17/67 |
| Tổng lỗ các tháng âm | −2.064 | −1.712 (+352, Šidák N = 20 [+91; +745]) |

- Walk-forward trên cả họ 20 ô: tổng lỗ tháng âm giảm +252 [+76; +490].
- Giảm lỗ ở 6/6 năm, 4/4 ô lân cận, 6/6 mốc cắt ngày.
- Thắng phép giả chốt ngẫu nhiên: p = 0,000.
- Nến 15m / 5m không hơn nến 1H.
- **Hạn chế:**
  - Chọn sau lưới, trên cùng mẫu dữ liệu (qs7 → qs10, `tbc1_merge`).
  - Lãi thêm dồn vào năm 2025 (+462).
  - Không giảm số tháng âm.
  - Cần theo dõi thực tế.

Tab «Tổng quan»: thẻ «PP1 + chốt lời». Chuỗi `pp1tp` trong `methods_bt.json` do `scripts/add_pp1tp_overview.py` thêm vào;
khi dựng lại `methods_bt.json` phải chạy lại script này.
