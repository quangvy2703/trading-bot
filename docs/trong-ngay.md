# Giao dịch trong ngày — bốn họ, không họ nào qua

**Ngày chạy:** 27/10/2026 · **Dữ liệu:** nến 1H perp Binance, 73 mã từng vào
top 10 thanh khoản, đo từ 2021-04-01 · script `scripts/intraday_scan.py`
(luật trong docstring, viết trước khi chạy)

Vũ trụ giống bot: top 10 theo hạng của ngày UTC đã đóng trước ngày giao
dịch. Mỗi lệnh 1/10 vốn, không đòn bẩy, lời/lỗ ghi vào ngày đóng lệnh. Phí
**10 bps** khứ hồi để quyết; 4 bps (maker) chỉ để tham khảo — lệnh phá vỡ
và lệnh bắt cú sốc là lệnh đuổi giá, thực tế khó khớp maker.

| Họ | Lưới | Ô chọn | Sharpe | lời/năm | bps/lệnh | Kết quả |
|---|---|---|---|---|---|---|
| F1 động lượng trong ngày (Gao et al. 2018; Wen et al. 2022) | giờ h 2/4/8/12 × ngưỡng k 0/0,5/1σ × chiều = 24 | h 8, k 1σ, chỉ mua | 0,56 | +8,5% | +26,1 | **loại** — KTC chứa 0, âm ở mốc cắt 16h |
| F2 phá vỡ biên độ (Larry Williams) | k 0,3/0,5/0,7/1,0 × lọc MA5 × chiều = 16 | k 1,0, lọc MA5, chỉ mua | 0,71 | +6,6% | +28,8 | **loại** — KTC chứa 0, âm ở mốc cắt 16h |
| F3 mùa vụ theo giờ UTC, tiến bước | n 1/2/3 giờ × cửa sổ ước 365 ngày / toàn bộ = 6 | — | **−3,2** | — | −11,8 | **chết** — mọi ô âm, cả ở 4 bps |
| F4 đảo chiều sau cú sốc 1H | z 2/3/4σ × giữ 1/4/12 giờ × chiều = 18 | z 4σ, giữ 4 giờ, chỉ mua | 0,55 | +6,9% | +34,9 | **loại** — KTC chứa 0 |

Luật chốt (cả bốn phải đạt): KTC Bonferroni 64 ô (99,92%) của lời ngày > 0
· ≥ 4/6 năm dương · F1/F2 dương ở cả 6 cách cắt ngày · ≥ 2/3 lân cận dương.

## Từng họ

**F1 — động lượng trong ngày.** Vào theo chiều của lợi suất từ đầu ngày tới
giờ h, ra cuối ngày. Hai chiều thì âm gần như mọi ô; chỉ sống ở **chỉ mua,
ngưỡng cao** (cú tăng > 1σ trong 8–12 giờ đầu). Theo năm +27,5 / −5,5 / +5,4 /
−4,3 / +2,1 / +22,1% — dồn vào 2021 và 2026.

**F2 — phá vỡ biên độ.** Mua khi giá vượt `open + k × biên độ hôm qua`, ra
cuối ngày. Hai chiều thì âm ở mọi ô; **chỉ mua, k lớn** thì dương. Đường đi
đơn điệu theo k (0,3 → 1,0: Sharpe −0,43 → +0,62 không lọc) — mẫu hình thật,
nhưng chính là mua cú tăng mạnh trong thị trường tăng.

**F3 — mùa vụ theo giờ.** Ước giờ tốt / giờ xấu từ quá khứ, giao dịch năm
sau. Lợi suất theo giờ chỉ vài bps, phí 10 bps mỗi lần vào ra — chết ở mọi
ô, kể cả 4 bps. Mùa vụ giờ trong crypto có thể có thật, nhưng không đủ lớn
để giao dịch.

**F4 — đảo chiều sau cú sốc.** Mua sau một giờ giảm > 4σ, giữ 4–12 giờ:
+35 đến +45 bps/lệnh, 4/4 lân cận dương. Chiều bán (bán sau cú tăng sốc)
thì âm. Chỉ ~200 lệnh/năm trên top 10; 2025 −10%.

## Ba điều rút ra

1. **Mọi ô dương đều là "chỉ mua".** Hai chiều thì âm ở cả F1, F2, F4. Trong
   2021–2026 thị trường đi lên, nên một phần những gì trông như lợi thế là
   beta — giữ long vài giờ trong thị trường tăng. Chưa tách bằng đối chứng
   mua ngẫu nhiên vì không ô nào qua được bước trước.
2. **Cắt ngày ở 16:00 UTC làm hỏng cả F1 lẫn F2** — giống RSI(2) 1D
   (`rsi2-connors.md`: mốc 08–20h ≈ 0). Ba chiến lược độc lập cùng tệ khi
   "ngày" kết thúc giữa phiên Mỹ. Đó là một quan sát về cấu trúc phiên, chưa
   phải tín hiệu.
3. **Phí là thứ quyết định ở khung giờ.** Lợi thế mỗi lệnh 25–45 bps ở ô tốt
   nhất, phí 10 bps — tỉ lệ 3–4 lần, đúng vùng mà RSI(2) 4H cũng rơi vào. Ở
   4 bps (maker) Sharpe tăng 0,15–0,3, không đủ đổi kết luận nào.

## Giới hạn

- 73 mã có nến 1H — đủ phủ top 10 gần như mọi ngày (90–100%), nhưng không
  phải toàn vũ trụ.
- Không có nến dưới 1 giờ (trừ BTC), nên không dịch mốc cho F4 và không thử
  được các họ cần sổ lệnh hay nến phút (scalping, mở cửa phiên 15 phút).
- Chưa tính funding (lệnh trong ngày chỉ đi qua 0–2 mốc thanh toán).

## Kế toán phép thử

64 ô, họ riêng (không cộng vào kế toán cắt ngang của `xsmom-volnorm.md` hay
của RSI(2)).

---

# Đợt 2 — bốn họ khác bản chất, nến 15 phút

**Ngày chạy:** 27/10/2026 · nến 15 phút của 86 mã từng vào top 10
(`scripts/fetch_15m.py`, kho data.binance.vision) · script
`scripts/intraday2.py`, luật trong docstring · 94 ô, Bonferroni 99,95%.

Đợt 1 về bản chất vẫn là "theo xu hướng / bắt đảo chiều" trên 1H. Đợt này là
những họ trong ngày có cơ chế khác hẳn:

| Họ | Lưới | Ô tốt nhất | Sharpe | bps/lệnh ròng | Kết quả |
|---|---|---|---|---|---|
| G1 momentum "vùng nhiễu" (Zarattini, Aziz & Barbon 2024; Concretum cho BTC) | L 7/14/28 ngày × m 0,75/1/1,5 × mốc 30/60 phút × VWAP = 36 | L 14, m 1,5, mốc 60 phút | **−1,11** | −8,1 | **chết** — 36/36 ô âm, ở cả 6 cách cắt ngày và cả 4 bps |
| G2 phá vỡ dải giá đầu phiên (Á 00:00, Âu 07:00, Mỹ 13:30) | phiên × dải 15/30/60 phút × giữ 4/8 giờ × chiều = 36 | Mỹ, dải 60 phút, giữ 8 giờ | −0,26 | −2,5 | **chết** — 36/36 ô âm ở 10 bps |
| G3 BTC dẫn altcoin, nến 15 phút | ngưỡng 1/2/3σ × giữ 1/2/4 nến × lọc phản ứng chậm = 18 | 3σ, giữ 4 nến, có lọc | −1,26 | −11,4 | **chết** — 18/18 ô âm, mọi năm âm |
| G4 mùa vụ thứ × phiên, tiến bước | n khối 1/2 × cửa sổ 365 ngày / toàn bộ = 4 | 1 khối, toàn bộ quá khứ | −0,06 | −1,3 | **chết** |

**Điểm chung: lời trước phí ≈ 0.** Gần như mọi ô lỗ đúng bằng phí (−8 đến −11
bps với phí 10). Tức là ở top 10 thanh khoản, khung 15 phút–8 giờ, các cơ chế
này **không có gì để thu** — không phải có mà bị phí ăn.

- **G1:** chiến lược công bố tốt nhất cho SPY không chuyển sang được crypto
  top 10. BTC riêng: +0,2 bps/lệnh trước phí trên 6.509 lệnh.
- **G2:** phiên Mỹ là phiên "ít tệ nhất" (ở 4 bps có ô +0,72), nhưng ba mốc
  giả 03:00 / 10:00 / 18:00 cho −0,51 / −1,68 / −1,54 — có chút khác biệt
  giữa giờ thật và giờ giả, quá nhỏ để giao dịch.
- **G3:** top 10 thanh khoản phản ứng theo BTC **trong cùng nến 15 phút** —
  không còn độ trễ để ăn. Bằng chứng trong tài liệu về độ trễ là ở coin nhỏ,
  kém thanh khoản — đúng nhóm bot không giao dịch.

## Còn lại gì trong giao dịch trong ngày

Những gì chưa thử đều cần **hạ tầng khác**, không chỉ dữ liệu khác:

- **Tạo lập thị trường / thu chênh lệch giá mua-bán:** cần sổ lệnh thời gian
  thực, độ trễ thấp, lệnh maker liên tục. Đây là nơi lợi thế trong ngày của
  crypto thật sự nằm, nhưng là một hệ thống khác hẳn bot chạy mỗi ngày một
  lần.
- **Dòng lệnh / mất cân bằng sổ lệnh ở mức giây:** cần dữ liệu tick (aggTrades
  / bookTicker), vài trăm GB cho top 10 × 5 năm.
- **Độ trễ BTC → coin nhỏ:** có bằng chứng, nhưng ở coin nhỏ chênh lệch giá
  mua-bán và trượt giá lớn hơn chính độ trễ.

Kế toán: đợt 2 thêm 94 ô, tổng giao dịch trong ngày 158 ô.
