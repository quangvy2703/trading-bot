# Luật cắt lệnh theo tick so với theo nến đóng — 06/11/2026, GIỮ NẾN ĐÓNG

Người dùng muốn mọi luật cắt lệnh chạy realtime, không đợi 15m / 1H / 4H. Một
số luật được nghiên cứu trên **nến đã đóng**, nên trước khi đổi cần backtest
lại phiên bản theo tick. Luật quyết viết trước trong
`scripts/tick_exits/tickgrid.py`.

## Cách đo

- **Engine:** bản sao engine nghiên cứu của bot đang chạy (qs14): Kase 2,2/30
  cho chân MUA động lượng, BSADF chặn BÁN, dừng an toàn 3R trên sàn, RSI(2)
  3 lớp với stop HVN, C4 = F08-1H + P16-1H. Nó tái lập đúng đường vốn của bot
  hiện tại (chênh 0).
- **"Tick"** được xấp xỉ bằng nến 1H (nến 15m cho windfall). Một lệnh thoát
  tick khi giá chạm mức bên trong nến và khớp đúng ở mức đó; nếu giá mở cửa đã
  vượt mức thì khớp ở giá mở.
- **Thứ tự trong cùng một nến:** nếu cắt lỗ / dừng an toàn và luật thoát chạm
  cùng một nến 1H thì tính cắt lỗ trước (thận trọng).
- **Đo trên cả bot:** lãi ngày USD (`methods_bt` + 5·Δ động lượng + Δ RSI(2),
  như qs14). ΔSharpe bootstrap khối 30 ngày ghép cặp, Šidák 10 → KTC 99,49%.
- **Luật quyết:** chuyển sang realtime chỉ khi KTC của ΔSharpe > 0 và ≥ 4/6
  năm ΔSharpe ≥ 0.

## Kết quả

Bot hiện tại: lãi 15.641 USD, Sharpe 2,455, sụt 900 USD, 17/67 tháng âm.

| Luật | Kiểm ở đâu | Δ lãi | ΔSharpe | KTC 99,49% | Năm ΔSh ≥ 0 | Quyết |
|---|---|---|---|---|---|---|
| RSI(2) > 70 | close 4H | −235 | −0,036 | [−0,082 ; +0,004] | 1/6 | giữ nến |
| | close 1H | −332 | −0,051 | [−0,105 ; −0,008] | 0/6 | **tệ hơn** |
| | tick (giá vượt P*) | −339 | −0,055 | [−0,120 ; +0,006] | 0/6 | giữ nến |
| Kase (chân MUA) | close 4H | −973 | −0,102 | [−0,408 ; +0,159] | 3/6 | giữ nến |
| | close 1H | −936 | −0,084 | [−0,430 ; +0,225] | 2/6 | giữ nến |
| | **tick** | **−2.485** | **−0,276** | [−0,752 ; +0,151] | 1/6 | giữ nến |
| C4 (chốt chân BÁN) | chỉ close 1D | −72 | −0,016 | [−0,081 ; +0,047] | 2/6 | giữ |
| | tick (lệnh chờ ở 0,5R / 1R) | −65 | +0,000 | [−0,040 ; +0,041] | 2/6 | ngang |
| Windfall k25 (chưa deploy) | tick so với close 15m | +152 | +0,018 | [−0,158 ; +0,171] | 4/6 | không rõ |
| **RSI + Kase + C4 cùng tick** | | **−2.890** | **−0,337** | [−0,837 ; +0,104] | **0/6** | giữ nến |

ΔSharpe theo năm (2021 → 2026):

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| RSI(2) tick | −0,065 | −0,143 | −0,021 | −0,066 | −0,055 | −0,023 |
| Kase tick | −0,072 | +0,010 | −0,191 | −0,695 | −0,119 | −0,330 |
| Tất cả tick | −0,170 | −0,158 | −0,173 | −0,779 | −0,205 | −0,366 |

## Đọc kết quả

- **Không luật nào tốt hơn khi kiểm theo tick.** Gộp cả ba luật đang chạy
  thì mất 2.890 USD, Sharpe 2,455 → 2,118, âm ở cả 6/6 năm.
- **RSI(2) theo tick bán sớm cú bật.** Giá vọt qua mức RSI 70 trong ngày rồi
  thường chạy tiếp tới lúc đóng cửa. Kiểm ở close 1H tệ hơn có ý nghĩa thống
  kê.
- **Kase theo tick cắt ở râu nến.** Số lần thoát tăng từ 558 lên 898, và năm
  2024 mất 0,7 Sharpe. Luật này chỉ đúng khi đọc giá đóng cửa ngày.
- **C4 theo tick ngang bản hiện tại.** Đặt lệnh chờ chốt lời ở mức 0,5R / 1R
  cho kết quả như kiểm mỗi giờ (ΔSharpe +0,000). Đổi cũng được, giữ cũng được.
- **Windfall** (chưa deploy) theo tick nhỉnh hơn bản close 15m (+152 USD) nhưng
  không có ý nghĩa thống kê. So với bot hiện tại, cả hai bản đều dương
  (+694 / +846 USD), đúng như qs14.

## Kết luận cho việc làm realtime

**Giữ luật nến đóng như đã backtest.** Phần realtime có ích là:

1. **Chạy ngay giây nến đóng** qua kline stream, thay vì chờ cron ở phút 1/2.
   Luật giữ nguyên, chỉ bớt độ trễ.
2. **User Data Stream** (`ACCOUNT_UPDATE` / `ORDER_TRADE_UPDATE`) để đối chiếu
   sổ với sàn ngay khi stop khớp hoặc khi đóng tay, thay cho vòng 5 phút.
3. **Luật theo mức giá:** cắt lỗ RSI(2), TSVW, DSRM và dừng an toàn 3R vốn đã
   là lệnh STOP_MARKET trên sàn, tức đã realtime. C4 dạng lệnh chờ trên sàn
   không làm kết quả tốt hơn hay tệ hơn.

Chưa đo:

- Chốt lời 2R / 1,5R của TSVW / DSRM khớp ngay tại mức thay vì ở open hôm sau.
  Nghiên cứu cũ (`tsvw-dsrm.md`, softexit) ước chênh chỉ +0,006 / +0,007R mỗi
  lệnh.
- VSA và C13 thoát theo giờ cố định (giữ 12 giờ / đóng ở close ngày), nên không
  có khái niệm tick.

Kế toán: RSI(2) +3 ô (≈ 478); động lượng / cắt ngang +7 ô (Kase 3, C4 2,
windfall 1, tất cả 1) → **1.438**.
