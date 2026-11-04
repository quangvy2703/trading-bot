# Động lượng (PP1): stop Kase cho chân mua + chặn bán theo funding / BSADF

Đưa vào bot ngày 04/11/2026 theo yêu cầu vận hành. Code ở `app/pp1x.py`, gọi
từ `runner.build_target`. Mỗi luật có **công tắc riêng**:

| Công tắc | Biến môi trường (giá trị đã chốt) | Bật/tắt lúc chạy |
|---|---|---|
| Stop Kase | `XSMOM_KASE=1` | tab «Cấu hình» → «Luật phụ động lượng» → `xsmom_kase` (1 bật, 0 tắt) |
| Chặn bán theo funding — **ĐÃ TẮT 04/11/2026** | `XSMOM_FUND_VETO=0` | `xsmom_fund_veto` (1 bật, 0 tắt) |
| Chặn bán theo BSADF (thêm cùng ngày) | `XSMOM_BSADF=1` | `xsmom_bsadf_veto` (1 bật, 0 tắt) |

Tắt luật nào thì từ lượt chạy kế tiếp bot chạy lại đúng như trước. Vị thế đã
đóng không bị mở lại ngay.

## Luật 1 · Stop Kase (chỉ chân MUA của động lượng)

- **Biên độ 2 nến:** DTR = max(H, H hôm qua, C hai hôm trước) − min(L, L hôm qua, C hai hôm trước).
- **Mức stop:** đỉnh cao nhất kể từ nến vào lệnh − (trung bình DTR 30 nến + 2,2 × độ lệch chuẩn DTR 30 nến).
  Mức này chỉ được đi lên. Tham số đặt bằng `XSMOM_KASE_K`, `XSMOM_KASE_N`.
- **Khi nào đóng:** ở lượt 00:05, nếu giá đóng cửa của nến ngày vừa đóng thấp hơn mức stop thì đóng vị thế.
  Lệnh đi qua đúng đường đóng của lần tái cân bằng; lý do đóng ghi là «Kase: …».
  Không có lệnh stop treo trên sàn cho luật này; stop an toàn 3R vẫn nằm trên sàn như cũ.
- **Mở lại:** mã vừa đóng không được mở lại trong cùng lượt. Ở lần tái cân bằng sau của sổ đó,
  nếu mã vẫn được chọn thì mở lại bình thường.
- **Không áp dụng cho:** chân bán, RSI(2), TSVW, DSRM.

## Luật 2 · Không mở lệnh BÁN động lượng khi funding toàn thị trường cực thấp — ĐÃ TẮT

**04/11/2026:** gỡ khỏi bot theo yêu cầu vận hành, vì luật không ổn định:
- Năm 2022 lỗ −60 USD.
- Đổi cách tính phân vị (toàn lịch sử hay 365 ngày) thì kết quả nhảy từ +100 đến +215 USD.
- Khoảng một nửa số lệnh nó chặn cũng là lệnh BSADF chặn.
- Kase + BSADF không có funding vẫn cho +451 USD, Sharpe 1,97.

Code vẫn giữ lại; muốn bật thì đặt `XSMOM_FUND_VETO=1`. Trên tab «Tổng quan», luật nằm ở mục «có thể thêm».

- **Chỉ số:** lấy funding theo ngày UTC của từng mã, tính trung bình 3 ngày. Rồi lấy trung vị
  trên top 50 thanh khoản, xếp theo trung vị giá trị giao dịch 30 ngày.
- **Phân vị:** xếp giá trị hôm nay so với **toàn bộ lịch sử trước đó**, cần ít nhất 180 ngày.
- **Khi nào chặn:** phân vị ≤ 10% (`XSMOM_FUND_PCT`) vào bất kỳ ngày nào trong 3 ngày gần nhất
  (`XSMOM_FUND_HOLD`). Khi đó lần tái cân bằng hôm nay **không mở lệnh bán mới**.
  Chỗ trống để trống, không lấy mã kế tiếp thay vào.
- **Không đổi:** lệnh bán đang giữ, chân mua và các chiến lược khác.
- **Lý do:** phe bán đang quá đông thì dễ bị ép ngược (short squeeze).

## Bằng chứng (backtest 04/2021 → 10/2026, engine thật, vốn 500, 1R = 2 USD)

| | Lãi thêm | Sharpe (mốc 1,52) | KTC 95% | KTC Šidák (1.387 ô) |
|---|---|---|---|---|
| Kase 2,2/30 | +262 USD | 1,75 | [+0,02; +0,52] | [−0,12; +0,65] |
| Funding p10 / 3 ngày | +100 USD | 1,65 | [−0,01; +0,29] | [−0,06; +0,44] |
| **Cả hai** | **+362 USD** | **1,90** | [+0,09; +0,75] | [−0,03; +1,01] |

- Theo năm, cả hai luật (USD): 21 +166 · 22 +5 · 23 −3 · 24 +38 · 25 +12 · 26 +144.
  Tháng lỗ giảm 28 → 24; tháng tệ nhất không đổi (−13,7%).
- Riêng tháng 3/2026 đóng góp khoảng một phần ba phần lãi thêm.

Phép thử ngẫu nhiên:
- Kase: đóng sớm ngẫu nhiên cùng số lần chỉ được trung bình +28 USD (p = 0,000).
- Funding: bỏ ngẫu nhiên cùng số lệnh bán cho p = 0,000; dịch thời gian chuỗi ngày chặn cho p = 0,007.

**Giới hạn:**
- Cả hai luật được chọn **sau khi** xem lưới 1.387 / 1.260 ô của đợt quét web.
- KTC Šidák vẫn chứa 0.
- Chưa kiểm độ bền theo mốc cắt nến khác 00h UTC.
- Tab «Tính lịch sử» của app **chưa** mô phỏng hai luật này.

**Theo dõi:** sau khoảng 6 tháng, so phần lãi thêm thực tế với khoảng +5 USD/tháng của backtest
(+362 USD / 67 tháng). Âm rõ thì tắt bằng công tắc.

Kiểm tra code: `app/pp1x.py` tái lập đúng nghiên cứu.
- Ngày chặn bán: 396/396 ngày khớp, 0 ngày lệch.
- Kase: 558/558 lần đóng khớp đúng ngày của engine nghiên cứu.


## Luật 3 · Không mở lệnh BÁN động lượng khi mã đang "nổ" (BSADF)

Luật lấy từ López de Prado, *Advances in Financial Machine Learning*, ch.17 (Phillips–Shi–Yu).
Bot thêm luật này ngày 04/11/2026.

- **Chỉ số:** chạy ADF trên log close của mã, `Δy_k = a + b·y_{k−1} + c·Δy_{k−1}`, cho mọi cửa sổ kết thúc
  ở nến hôm nay, độ dài từ 30 đến 90 nến. Lấy t-stat của b lớn nhất (sup) = BSADF.
- **Khi nào chặn:** BSADF > 0,531. Đây là ngưỡng 95% Monte Carlo, tính trên 2.000 bước ngẫu nhiên với seed 7.
  Tham số đặt bằng `XSMOM_BSADF_W` / `_W0` / `_CV`.
- **Thực chất:** luật chặn bán vào những cú **sập đang tăng tốc**. Mọi lệnh bị chặn đều là mã đã giảm 20 ngày;
  các lệnh bán đó lỗ trung bình −0,4R. Luật không bắt bong bóng giá tăng.
- Mã bị chặn để trống chỗ, không lấy mã kế tiếp thay vào.

### Engine thật: mọi tổ hợp (so với mốc chưa có luật phụ, Sharpe 1,52)

| Tổ hợp | Lãi thêm | Sharpe | KTC Šidák (20 ô) | Sụt | Tháng lỗ | Năm 21…26 (USD) |
|---|---|---|---|---|---|---|
| Kase + funding (đang chạy trước đó) | +362 | 1,90 | [+0,00; +0,88] | 197 | 24 | +166 +5 −3 +38 +12 +144 |
| BSADF một mình | +189 | 1,71 | [+0,04; +0,38] | 188 | 25 | +25 +35 +51 +20 +50 +9 |
| **Kase + BSADF** (BSADF thay funding) | **+451** | 1,97 | [+0,10; +0,89] | **175** | **21** | +102 +100 +29 +53 +48 +119 |
| Kase + funding + BSADF | +444 | **2,01** | [+0,07; +1,04] | 175 | 22 | +162 +22 +30 +52 +37 +141 |

**So với Kase + funding:**
- thêm BSADF: +83 USD, Sharpe +0,10, KTC 95% [+0,01; +0,20];
- thay funding bằng BSADF: +89 USD, Sharpe +0,06.

**Lưới W × w0** (90/180/365 × 20/30) đều dương: một mình +149…+189 USD; cộng Kase + funding thì +421…+444 USD.

**Funding và BSADF trùng nhau khoảng một nửa số lệnh bị chặn.** Bật cả hai hay chỉ bật BSADF cho kết quả gần như nhau.
Bản chỉ có BSADF đều hơn giữa các năm (năm 2022: +100 so với +22).

Kiểm tra code: `pp1x.bsadf_at` khớp bản numba của nghiên cứu đến 1e-11 trên 173 điểm, 0 lệch cờ.
