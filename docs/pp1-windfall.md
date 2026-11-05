# PP1 · windfall nến 15m (k 25, mở lại)

Thêm vào bot ngày 06/11/2026.
- Code: `app/pp1wf.py`.
- Công tắc: `xsmom_wf` / `XSMOM_WF`, mặc định bật.
- Áp cho cả hai chân PP1, ở chế độ đang chạy: sổ giấy, hoặc lệnh thật khi đã bật `live_armed`.
- Ý tưởng do người dùng đưa ra.

## Luật
Bot kiểm ở phút 1/16/31/46 mỗi giờ, trên nến 15m vừa đóng của mỗi lệnh PP1:

z = ln(C_t / C_{t−1}) ÷ sd(288 log-return 15m trước đó, không gồm nến t; ddof 1; cần ≥ 90% có số liệu)

| Bước | Điều kiện | Tham số |
|---|---|---|
| **Đóng** | chiều × z ≥ K → đóng toàn bộ lệnh ở giá thị trường (≈ giá mở nến 15m kế tiếp) | `XSMOM_WF_K` 25 · `XSMOM_WF_TF` 15m · `XSMOM_WF_W` 288 · `XSMOM_WF_SIDE` both |
| **Mở lại** | ở lượt ngày 00:05 đầu tiên sau giờ đóng, nếu sổ của lệnh không đến lượt tái cân bằng hôm đó: mở lại cùng sổ / mã / chiều, cỡ lệnh 1R/(σ30·√7) tính ở giá mới | `XSMOM_WF_RE` 1 |

- Nếu sổ đến lượt tái cân bằng đúng hôm đó, lần tái cân bằng quyết định.
- Khi mở lại không kiểm lại lọc MA và BSADF, vì sổ vẫn giữ mã đó, giống engine nghiên cứu.
- Lệnh chặn mua do huỷ niêm yết vẫn áp dụng.
- Ở nến 00:00 UTC, bỏ qua sổ sẽ tái cân bằng lúc 00:05.
- Lệnh đã dính stop 3R trên sàn thì không còn trong sổ.
- Lãi/lỗ đã chốt cộng vào `tp_realised:<mode>`, dùng chung với C4.
- Danh sách chờ mở lại lưu ở kv `pp1wf_reenter`; lượt kiểm gần nhất lưu ở `pp1wf_last`. `/api/state` trả về cả hai.
- Lệnh bán mở lại vẫn chịu C4; F08 và P16 tính lại từ lúc mở lại.

## Bằng chứng
Engine B10+K + C4, bot 6 PP ở hệ số 5/8/5/5/5/5, **không trần**, 07/04/2021 → 25/10/2026. Scratch 84a09f4d: `qs11/pp1` (windfall chạy riêng) và `qs14` (chạy trên nền C4).

| | C4 (mốc) | C4 + windfall k25, mở lại |
|---|---|---|
| Lãi | 15.641 | 16.336 (+694) |
| Sharpe | 2,455 | 2,558 (Šidák-6 [+0,010; +0,246]) |
| Sụt lớn nhất | 900 | 889–898 |
| Tháng âm | 17/67 | 16/67 (2025-10 −132 → +21; không có ý nghĩa thống kê) |

- Δ ≥ 0 ở 6/6 năm.
- Dương cả giai đoạn dev (+539) lẫn holdout (+155).
- 6/6 ô lân cận (k 20/25/30 × có/không mở lại) đều dương.
- Giữ được 89–108% phần lãi so với khi chạy windfall riêng.

**Hạn chế:**
- 10 ngày tốt nhất chiếm toàn bộ phần lãi; bỏ 10 ngày đó thì Δ còn −133…+43. Đó chủ yếu là các ngày sập chớp nhoáng: 11/10/2025, 18/08/2023, 29/05/2023.
- k được chọn trên cùng mẫu dữ liệu, và holdout đã dùng ở các nghiên cứu trước.
- Walk-forward khi chạy riêng (qs11) bị trượt.
- Cần theo dõi thực tế.

Tab «Tổng quan»: thẻ «PP1 + windfall». Chuỗi `pp1wf` trong `methods_bt.json` do `scripts/add_pp1wf_overview.py` thêm từ `qs14/pp1wf_R.npy`. Khi dựng lại `methods_bt.json` phải chạy lại script này, sau `add_pp1tp_overview.py`.
