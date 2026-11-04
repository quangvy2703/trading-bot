# BTC sập → cắt chân mua động lượng (SỔ GIẤY)

Nghiên cứu ngày 03/11/2026, theo câu hỏi "BTC sập nhanh thì cắt hết các lệnh
mua thì sao". **Trạng thái: sổ giấy.** App chỉ đọc sổ vị thế của chính bot rồi
ghi lại phần chênh. Nó **không bao giờ** đặt hay huỷ lệnh, và không đổi điều gì
bot đang làm (code: `app/crash.py`, tab «BTC sập (giấy)»).

## Luật (chốt trước khi sổ chạy, không đổi trong lúc chạy)

1. **Kích hoạt:** ngày UTC vừa đóng có BTC close / close hôm trước − 1 ≤ **−5%**.
2. **Luật giả:** đóng **mọi vị thế MUA của động lượng** (xsmom) ở giá close
   ngày đó. Không mở lệnh mua động lượng mới trong **7 lượt chạy**, tính cả
   lượt kích hoạt. Nếu kích hoạt lại trong lúc đang chặn thì kéo dài thêm 7
   lượt tính từ lần mới.
3. **Không đụng tới** RSI(2), TSVW, DSRM và chân BÁN của động lượng.

## Sổ ghi gì

Với mỗi vị thế mua động lượng bị luật đụng tới, sổ ghi phần chênh USD giữa
"bot thật" và "bot có luật":

- **cắt**: vị thế đang giữ lúc kích hoạt. Chênh = qty × (giá close ngày kích
  hoạt − giá lúc kết thúc).
- **bỏ qua**: vị thế bot mở trong lúc chặn. Chênh = −(lãi/lỗ của vị thế đó).

Một dòng kết thúc khi bot thật đóng vị thế. Nếu bot vẫn giữ, dòng kết thúc ở
lượt đầu tiên **sau khi hết chặn** mà sổ của vị thế tới lượt tái cân bằng. Từ
lúc đó bot có luật sẽ mở lại nếu mã vẫn được chọn, nên hai thế giới trùng nhau.

Phí 10 bps khứ hồi được tính như engine backtest:
- dòng **cắt** mà bot vẫn giữ đến hết chặn phải trả thêm 10 bps (đóng rồi mở lại);
- dòng **bỏ qua** mà bot đã đóng trong lúc chặn được tiết kiệm 10 bps.

Funding không tính.

## Backtest (04/2021 → 10/2026, cấu hình đang chạy: stop trên sàn + trần thật)

Lưới 24 ô gồm: kiểu cắt {theo ngày, theo giờ} × ngưỡng {5, 8, 10, 15}% × số
lượt chặn {1, 3, 7}. Mỗi ô có phép giả dùng ngày ngẫu nhiên, cùng số lần kích
hoạt. Ô này là ô theo ngày, 5%, 7 lượt:

| | Mốc | Có luật |
|---|---|---|
| Lãi PP1–PP4 (vốn 500, 1R = 2 USD) | 2.153 USD | **+251 USD** |
| Phần chênh chỉ ở động lượng | — | +237 USD = **+118 R**, ≈ **+1,5 R mỗi lần kích hoạt** |
| Sụt lớn nhất | 212 USD | 188 USD |
| Chênh Sharpe ngày | — | +0,15, KTC Šidák 24 ô **[−0,27; +0,58]** |
| Phép giả (ngày ngẫu nhiên) | — | TB −0,19, p95 +0,10 → ô vượt |

- Số lần kích hoạt: 77 lần trong 5,5 năm, khoảng 14 lần/năm. Luật chặn mua
  21% số ngày.
- **Đạt 4/5 luật, trượt luật KTC**, nên chỉ được ghi sổ giấy, không được đưa vào
  bot thật.
- Cắt cả RSI(2) thì **lỗ** (−62 USD), vì RSI(2) vốn mua đáy.
- Cắt **theo giờ** (rơi 5% so với đỉnh 24 giờ) **hại**: −276 USD, vì bán đúng
  đáy của các cú sập trong ngày.
- Luật phần ghi trên được rút ra **sau khi** nhìn lưới (chỉ chân mua động
  lượng). Vì vậy sổ giấy là phép thử ngoài mẫu thật sự đầu tiên.

## Khi nào xét lại

Sau **≥ 12 lần kích hoạt** (khoảng 1 năm), so số R mỗi lần kích hoạt trong sổ
với **+1,5 R** của backtest. Chỉ đề xuất đưa vào bot thật nếu cả ba điều sau
cùng đúng:
- tổng chênh dương;
- số R mỗi lần không dưới một nửa backtest;
- không có một lần kích hoạt đơn lẻ nào chiếm quá nửa tổng chênh.
