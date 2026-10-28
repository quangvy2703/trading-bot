# Stop ở đỉnh / đáy cũ — bốn cách xác định, ba chỗ dùng, không chỗ nào hơn

**Ngày chạy:** 28/10/2026 · script `scripts/swing_stops.py` (luật trong
docstring, viết trước khi chạy) · nến D, lệnh thật của engine «Tính lịch sử»
(ALLOC 8/1), 2021-04 → 2026-10 · 96 ô

## Bốn cách xác định đỉnh / đáy cũ (tất cả nhân quả)

| Cách | Tham số | Biết được khi nào |
|---|---|---|
| Pivot / fractal | thấp nhất trong N nến hai bên, N 2/3/5 | N nến sau đáy |
| Donchian | thấp nhất N nến gần nhất, N 5/10/20 | ngay lập tức |
| ZigZag | đáy xác nhận khi close bật lên ≥ k×ATR, k 1/2/3 | khi giá bật đủ k |
| Nổi bật (prominence) | đáy ZigZag + bên trái cũng có đỉnh cao hơn ≥ k×ATR trong 20 nến | như ZigZag |

Chỉ dùng điểm **đã xác nhận trước ngày vào lệnh**, tối đa 60 nến về trước.
Stop mua = đáy gần nhất (mới nhất) nằm dưới giá vào − đệm; bán = đỉnh gần
nhất trên giá vào + đệm. Đệm 0 / 0,25×ATR.

**Nổi bật cho kết quả gần như trùng ZigZag** ở k 1 và 2: đáy ZigZag đã có
sẵn một đỉnh ZigZag ≥ k×ATR ngay bên trái, nên điều kiện bên trái hầu như
không loại thêm gì. Chỉ ở k 3 hai cách mới tách nhẹ (92% so với 93% phủ).

## A — lệnh nhồi động lượng (thay cắt lỗ −1 ATR)

Lệnh nhồi giữ nguyên điểm kích hoạt (giá đi đúng 1 ATR). Cắt lỗ ở đáy/đỉnh
cũ; chốt lời RR 1:1 theo khoảng stop, hoặc +1 ATR cố định. Mốc: khung ±1 ATR
= **+0,085R/lệnh** (`xsmom-volnorm.md` § Lệnh nhồi có khung).

| | tốt nhất mỗi cách (R/lệnh) |
|---|---|
| **mốc ±1 ATR** | **+0,085** |
| Donchian 10–20 | +0,048 … +0,056 |
| Pivot 2–3 | +0,038 … +0,049 |
| ZigZag / nổi bật | +0,003 … +0,039 |

Không ô nào bằng mốc. Chốt lời +1 ATR với stop ở đáy cũ cho tỉ lệ thắng
75–90% nhưng lời nhỏ hơn: stop xa, chốt gần — mỗi lần thua mất nhiều R hơn
mỗi lần thắng được. **Ô chọn (Donchian 20, đệm 0,25, RR 1:1): +0,056,
KTC chứa 0, kém mốc → không đạt.**

## B — lệnh gốc động lượng (thêm stop, hiện không có)

Lãi ghi vào ngày ra lệnh (không đánh giá lại hằng ngày) nên Sharpe ở đây cao
hơn bảng khác — chỉ dùng để so giữa các ô.

| | lãi USD | Sharpe | sụt USD |
|---|---|---|---|
| **gốc (không stop)** | 52.998 | 2,11 | 8.045 |
| ZigZag / nổi bật k 3 | 56.093 … 56.555 | 2,16 … 2,17 | 6.190 … 6.257 |
| Pivot 5 | 51.303 … 53.167 | 1,84 … 1,90 | 6.798 … 6.968 |
| Donchian 5 | 35.214 … 38.515 | 1,49 … 1,53 | 7.441 … 7.560 |

Stop **gần** (Donchian 5, pivot 2–3, ZigZag 1) làm hại: cắt lệnh động lượng
trước khi nó chạy. Stop **xa** (ZigZag 3) gần như không đổi gì nhưng cắt sụt
~23%. Ô chọn (nổi bật 3, đệm 0,25): Sharpe 2,17 so với 2,11, hơn gốc chỉ 3/6
năm, lân cận 1/2 → **không đạt.** Ghi chú cho sau: stop ZigZag 3 làm sụt nhỏ
hơn mà không mất lãi — đáng thử lại nếu có lúc cần giảm sụt.

## C — lệnh gốc RSI(2) (thay stop 6×ATR)

Định cỡ theo R: stop gần → lệnh **to hơn** cho cùng 1R, nên R/năm tăng — nhưng
sụt tăng nhanh hơn, và phí ăn vào R nhiều hơn.

| | stop TB | R/lệnh | R/năm | sụt R | R/năm÷sụt |
|---|---|---|---|---|---|
| **gốc 6×ATR** | 35,5% | +0,062 | +1,74 | 2,02 | **0,86** |
| ZigZag 2, đệm 0,25 | 27,2% | +0,086 | +2,43 | 2,61 | 0,93 |
| Pivot 5 | 23,3% | +0,107 | +3,02 | 3,23 | 0,93 |
| ZigZag 3, đệm 0,25 (ô chọn) | 29,9% | +0,081 | +2,28 | 2,59 | 0,88 |
| Donchian 5, đệm 0,25 | 5,4% | +0,215 | +6,58 | 9,25 | 0,71 |
| Pivot 2 | 12,9% | +0,015 | +0,43 | 11,06 | 0,04 |

Ô chọn: hơn gốc 5/6 năm, nhưng điểm 6 cách cắt ngày **+0,22 so với +0,25** của
gốc, lân cận 1/2 → **không đạt.** Kết luận cũ của `rsi2-connors.md` vẫn đứng:
stop gần đáy cắt đúng phần đáy mà RSI(2) đang chờ bật; ở R thì lệnh to hơn
chỉ đổi lấy sụt to hơn.

## Kết luận

Ở cả ba chỗ, **stop ở đỉnh/đáy cũ không hơn stop đang dùng** (±1 ATR cho lệnh
nhồi, không stop cho động lượng, 6×ATR cho RSI(2)). Quy luật chung: stop càng
gần đáy cũ thì càng tệ, vì đáy cũ gần nhất nằm ngay trong vùng nhiễu bình
thường của giá. Khi đủ xa để không bị nhiễu chạm (ZigZag 3 ATR) thì nó gần như
trùng với stop theo ATR đang có.

---

# Volume profile — cắt lỗ / chốt lời ở đỉnh khối lượng gần nhất

**Ngày chạy:** 28/10/2026 · script `scripts/vp_stops.py` (luật trong docstring)
· 96 ô

Profile dựng từ nến 1H của L ngày **trước** điểm quyết định: khối lượng USD
mỗi nến đặt vào giá điển hình, ô rộng w×ATR, làm mượt [1,2,1]. Hai cách lấy
"mức max gần nhất": **HVN** — đỉnh khối lượng cục bộ (≥ TB profile) gần giá
nhất; **POC phía đó** — ô khối lượng lớn nhất ở phía dưới (cắt lỗ) / phía trên
(chốt lời). Lưới: L 5/20/60 ngày × w 0,25/0,5 ATR × HVN/POC × đệm 0/0,25 ATR.
Không có mức hợp lệ → giữ stop gốc (cột "phủ").

| Chỗ dùng | Kết quả | |
|---|---|---|
| **A** lệnh nhồi động lượng (cắt lỗ + chốt lời ở mức profile) | HVN chỉ phủ 0–6% lệnh; POC phủ 35–53% nhưng R/lệnh −0,04 … +0,02 so với mốc ±1 ATR **+0,08 … +0,12** trên cùng lệnh | **không đạt** |
| **B** lệnh gốc động lượng (thêm cắt lỗ) | POC 5 ngày cắt sụt gần một nửa (4.390 so với 8.045 USD), Sharpe 2,22 so với 2,11, nhưng lãi giảm 14% và hơn gốc chỉ 3/6 năm | **không đạt** |
| **C** lệnh gốc RSI(2) (cắt lỗ thay 6×ATR) | ô L20 · w 0,5 · HVN · đệm 0,25: R/năm÷sụt **1,85** so với 0,86, hơn 6/6 năm, 6 cách cắt +0,77 so với +0,25, lân cận 5/6 | **đạt theo luật** — xem cảnh báo |

## C — đạt luật, nhưng phần lớn là đòn bẩy

Mổ xẻ sau khi đạt (nhìn sau, không đổi kết luận luật):

```
lệnh ứng viên có mức HVN     77 (44% số lệnh được lấy)
khoảng stop TB               HVN 11,8%  ·  6×ATR 34,5%
tỉ lệ chạm stop              HVN 19,5%  ·  6×ATR 0,0%
lợi suất giá TB              HVN +282 bps  ·  6×ATR +319 bps
R/lệnh                       HVN +0,464  ·  6×ATR +0,095
bị HVN cắt                   15 lệnh, chỉ 1 trong số đó về sau có lời ở bản 6×ATR
Sharpe R theo tháng          HVN 1,22  ·  6×ATR 1,11
chênh Sharpe                 KTC95 [−0,54 ; +0,77] · KTC Bonferroni 96 ô [−1,20 ; +1,22]
```

Hai điều đúng cùng lúc:

1. **Stop ở HVN không làm hỏng lệnh.** Lợi suất giá gần như giữ nguyên (+282
   so với +319 bps): 14/15 lệnh bị cắt là lệnh vốn sẽ lỗ. Đây là khác biệt
   thật so với stop ở đáy cũ (pivot, Donchian…), vốn cắt nhầm lệnh tốt.
2. **Phần lớn cải thiện R/năm là cỡ lệnh.** Stop gần gấp 3 lần → cùng 1R thì
   lệnh to gấp ~3 lần trên 44% số lệnh. Thước đo luật (R/năm ÷ sụt trên chuỗi
   lệnh đã chốt) không bất biến khi chỉ một phần lệnh được phóng to — đây là
   điểm yếu của thước đo, phát hiện sau khi chạy. Sharpe theo tháng chỉ tăng
   0,11 và **KTC chứa 0**.

**Cách đọc:** stop HVN là một cách đặt stop **gần hơn mà không bị nhiễu chạm**
— đúng điều mà mọi cách đỉnh/đáy cũ khác không làm được. Nhưng lợi ích đo
được là "dùng được lệnh to hơn", và lệnh to gấp 3 lần (stop 11,8% → danh
nghĩa ≈ 8,5R) sẽ đụng `MAX_ORDER_USD` và ký quỹ trước. Chưa đủ để thay 6×ATR:
77 lệnh, Sharpe chênh không có ý nghĩa. Ứng viên cho sổ giấy.

### Đã bật trong bot — 28/10/2026 (lựa chọn vận hành)

Người vận hành chọn bật dù bằng chứng như trên: `RSI2_STOP_HVN=1`. Code ở
`trading-bot/app/volprofile.py`, khớp định nghĩa của `vp_stops.py` trên 400/400
mẫu. Hai thay đổi đi kèm vì lệnh to hơn:

- `MAX_ORDER_USD` 150 → **500**. Lệnh RSI(2) vượt trần được **thu nhỏ về đúng
  trần** (rủi ro < 1R, ghi «thu về trần … R») thay vì bị bỏ. Ở mức 500 có
  ~4,5% lệnh bị thu nhỏ; ở mức 150 là 21%.
- `MAX_GROSS_USD` → **1.500**, để hai tín hiệu cùng ngày không chặn nhau.

Mỗi tín hiệu mới bot lấy 20 ngày nến 1H từ bảng `bars1h`, tải bổ sung top 20
mỗi lượt chạy. Lỗi mạng hoặc không có HVN thì dùng 6×ATR. Tab «Tính lịch
sử» mô phỏng y như vậy. Với cấu hình đang chạy, kết quả của tab nằm ở
[rsi2-connors.md](rsi2-connors.md) § Bot đang chạy gì.

---

# Điểm chốt lời cho RSI(2) với stop HVN — 28/10/2026, GIỮ thoát RSI > 70

Script `scripts/rsi2_tp.py` (luật trong docstring). Stop HVN như bot đang
chạy; mốc = chỉ thoát khi RSI(2) > 70. 22 ô: chốt lời ở 1/1,5/2/3 R, 1/2/3
ATR, HVN phía trên, POC phía trên, đỉnh 10/20 ngày × {vẫn thoát RSI > 70, bỏ
thoát RSI}. Thước đo chính: **Sharpe R theo tháng** (bài học từ stop HVN).

| | R/năm | sụt R | Sharpe tháng |
|---|---|---|---|
| **mốc: chỉ RSI > 70** | +5,81 | 3,14 | **1,16** |
| + chốt 2–3 R / 2–3 ATR / đỉnh cũ | +5,1 … +5,8 | 3,14 | 1,14 … 1,16 |
| + chốt 1 R / 1 ATR / POC | +3,7 … +4,3 | 3,12 … 3,14 | 1,11 … 1,16 |
| HVN phía trên, **bỏ** RSI | +5,58 | 2,91 | 1,12 |
| R / ATR / đỉnh cũ, **bỏ** RSI | +2,1 … +4,4 | **8,7 … 19,1** | 0,34 … 0,51 |

- **Không chốt lời nào nâng được Sharpe** quá mốc. Chốt xa (≥ 2R, ≥ 2 ATR,
  đỉnh cũ) gần như không bao giờ chạm trước RSI > 70 — trùng mốc; chốt gần thì
  chỉ cắt bớt lệnh thắng.
- **Bỏ thoát RSI là thảm hoạ** (sụt ×3–6): RSI > 70 chính là thứ đóng lệnh
  khi cú bật đã xong; thiếu nó lệnh nằm chờ một mức giá có thể không bao giờ
  tới, rồi chạm stop.
- Ô chọn theo luật (POC phía trên, bỏ RSI): Sharpe 1,12, hơn mốc 2/6 năm,
  kém ở 5/6 cách cắt ngày → **giữ mốc**.
