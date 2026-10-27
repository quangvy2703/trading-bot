# Trade Explorer — thiet ke

**Muc tieu.** Chuyen viec do tham so cua luat vao lenh tu vong lap "sua script →
chay lai → dung lai trang tinh" thanh mot man hinh: chon config, bam chay, xem
tung lenh duoi dang the nho, sua TP/SL truc tiep.

**Ngoai pham vi.** `reports/trading_data.html` giu nguyen, khong gop vao. Do la
man xem toan canh (9 the du lieu phai sinh, keo/zoom qua nhieu nam); man nay la
man do tham so. Hai muc dich khac nhau, gop lai chi lam ca hai kem di.

## Luat ma app nay tinh

Luat da doi bon lan trong qua trinh do; day la ban app hien thuc, tuong ung
`RULE_VERSION = 5` va khop voi `scripts/bt_rule_extreme.py`:

```
loc chung   volume >= trung binh n nen TRUOC do
MUA         taker buy > 60%
            close > open
            rau tren <= wick x bien do nen
            OI tang lien tuc n phien  (OI[j] > OI[j-1] cho ca n buoc)
            high >= max(high cua n-1 nen truoc)
BAN         taker buy < 40%
            close < open
            rau duoi <= wick x bien do nen
            OI tang lien tuc n phien   (KHONG phan chieu -- ca hai ben deu doi
                                        OI tang, tuc tien moi vao vi the)
            low <= min(low cua n-1 nen truoc)
SL          day nen (mua) / dinh nen (ban)
TP          2R
vao lenh    gia MO cua nen KE TIEP
duong gia   do tren nen 5m, tran giu lenh 48h; cham ca TP lan SL trong cung
            mot nen 5m -> tinh la THUA
phi         taker 0,05% moi chieu
```

**Mot tham so `n` chi phoi ba cho**: chu ky trung binh volume, so phien OI phai
tang lien tuc, va be rong cua so xet cuc tri. Do la y dinh, khong phai thieu
sot — nguoi dung dat luat nhu vay.

`wick` la ti le so voi bien do nen, khong phai so tuyet doi. Mac dinh 10%; muc
0 (rau dung bang 0) hau nhu khong bao gio xay ra tren du lieu that (do duoc:
1-4 lenh trong 5,7 nam) nen UI canh bao khi chon 0.

## Rang buoc chi phoi thiet ke

Hai con so quyet dinh gan nhu moi lua chon duoi day, ca hai deu do duoc:

| viec | thoi gian |
|---|---|
| Tai du lieu mot symbol MOI (2.100 ngay) | ~11 phut (klines 5m ~470s + kho metrics ~205s) |
| Tinh tin hieu + mo phong bracket tren 50.401 nen | **< 1 giay** (numpy vector hoa) |

He qua: "render dan dan" phai gan vao pha TAI, khong phai pha TINH. Thiet ke
nao stream ket qua tinh theo lo la giai sai bai toan.

## Kien truc

```
trinh duyet                         serve.py (localhost)
  thanh config      --POST /api/run-->  khoa = hash(config)
  luoi the lenh     <--SSE tien do---   hit  -> tra ngay
  (lazy-load)                           miss -> tai (stream) + tinh
                                              |
                                        import (KHONG viet lai)
                                        scripts/backtest_taker_oi.py
```

**Nguyen tac bat buoc: khong nhan ban logic.** `serve.py` goi thang
`dataset / to_tf / signals / brackets` cua `backtest_taker_oi.py`. Moi con so
thong ke da cong bo deu do duong Python nay sinh ra; mot ban JavaScript song
song se troi khoi no ma khong ai phat hien.

### Cac don vi

| tep | trach nhiem | phu thuoc |
|---|---|---|
| `scripts/webapp/rules.py` | `RuleConfig` -> mat na tin hieu long/short | `backtest_taker_oi` |
| `scripts/webapp/jobs.py` | hang doi job, tien do, huy | `rules`, `backtest_taker_oi` |
| `scripts/webapp/store.py` | doc/ghi cache `runs/` va `edits/` | — |
| `scripts/webapp/serve.py` | dinh tuyen HTTP, SSE, phuc vu tinh | `jobs`, `store` |
| `static/app.js` | thanh config, luoi the, lazy-load, sua TP/SL | — |
| `static/card.js` | ve MOT the: 6 nen + TP/SL + tay cam | — |
| `static/index.html`, `static/app.css` | khung va kieu dang | — |

`card.js` tach rieng vi no la don vi duoc goi nhieu nhat (moi the mot lan) va
la cho duy nhat co logic keo-tha; giu no doc lap de test duoc bang mot bo nen
gia lap, khong can server.

## API

```
GET  /api/symbols                  -> [{sym, days, ready}]  symbol da co cache
POST /api/run                      -> {job, key, cached}
       {sym, tf, n, wick, days}
GET  /api/stream/<job>             -> SSE
       event: progress  {phase:"fetch"|"compute", done, total, msg}
       event: done      {key}
       event: error     {msg}
POST /api/cancel/<job>             -> {ok}
GET  /api/result/<key>             -> {config, funnel, trades[], summary, edits}
PUT  /api/trade/<key>/<i>          -> {r, bps, exit_t, exit_px}
       {tp, sl}
DELETE /api/edits/<key>            -> {ok}   xoa moi sua tay cua config nay
```

### Ban ghi mot lenh

```json
{"i":12,"side":"long","t":1755500400000,"entry":63036.1,"stop":62986.3,
 "tp":63135.7,"xt":1755512400000,"xp":63135.7,"r":2.0,"bps":5.8,"hrs":2.2,
 "bars":[{"t":...,"o":...,"h":...,"l":...,"c":...,"v":...}, ... 6 phan tu]}
```

`bars` la nen tin hieu + 5 nen ke, theo dung timeframe da chon. 400 lenh x 6 nen
~60 KB — nho hon mot lan goi API, nen the khong bao gio phai cho mang. Day la ly
do lazy-load o day chi con la "ve hay chua ve", khong phai "tai hay chua tai".

## Luong du lieu

1. Nguoi dung chon config, bam **Chay**.
2. `POST /api/run` bam khoa `key = sha1(sym|tf|n|wick|days|RULE_VERSION)`.
   - Co `runs/<key>.json` -> tra `{cached:true, key}`, frontend goi thang
     `/api/result/<key>`.
   - Khong co -> tao job, tra `{job, key}`.
3. Frontend mo `EventSource(/api/stream/<job>)`.
4. Job chay:
   - **pha fetch** (bo qua neu npz da co): phat `progress` moi 20 ngay tai xong.
   - **pha compute**: mot buoc, phat `progress {phase:"compute"}` truoc va sau.
   - ghi `runs/<key>.json`, phat `done`.
5. Frontend tai ket qua, dung luoi the, `IntersectionObserver` ve tung the khi
   no vao viewport.

## Lazy-load

`IntersectionObserver` voi `rootMargin: "400px 0px"` — ve truoc mot man hinh de
cuon khong thay o trong. The ra khoi vung do **2 man hinh** thi xoa noi dung SVG
va danh dau chua ve; vao lai thi ve lai. Nguong xoa rong hon nguong ve de tranh
ve-xoa lien tuc khi cuon qua lai quanh mot bien.

Do luong bat buoc truoc khi coi la xong: **1.000 the**, cuon het luoi, so phan
tu DOM khong duoc vuot 3x so the dang hien.

## Sua TP/SL

Keo tay cam tren the. Chon duong bang ham chon-duong-gan-nhat da co trong
`trading_data.html` (`pick()`, `BAND=14`) — no ton tai vi ban kiem-truoc-tien
lam mot trong hai duong khong bat duoc khi chung o gan nhau.

Tha ra -> `PUT /api/trade/<key>/<i>` voi `{tp, sl}`. **Server tinh lai** ket qua
tren duong gia 5m day du (tran 48h) roi tra `{r, bps, exit_t, exit_px}`. Khong
day duong 5m ve client: 400 lenh x 576 nen ~4 MB cho mot viec server lam trong
mot phan nghin giay.

Sua tay luu o `edits/<key>.json`. **Tom tat hien hai dong** — ban may tinh va
ban da sua — de khong lan. Nut `DELETE /api/edits/<key>` tra ve ban goc.

## Pheu dieu kien

Config chat cho luoi rong (do duoc: `n=20` cho 0 lenh). Thay vi luoi trong,
hien so nen song sot qua tung dieu kien:

```
dieu kien                 con lai   % con lai
tong so nen                50.401
du taker + OI              45.907       91,1%
vol >= MA(n)               18.040       39,3%
taker > 60%                   377        2,1%
close > open                  371       98,4%
rau tren <= 10%                93       25,1%
OI tang lien tuc n              6        6,5%
dinh cuc tri n                  6      100,0%
```

Do tren BTCUSDT 1h, 2.100 ngay, `n=5`, chieu MUA. Bang nay noi ngay hai dieu
ma khong bang thong ke nao noi duoc: `close > open` gan nhu khong cat gi (98,4%
song sot, vi taker > 60% da ham y nen xanh), con `OI tang lien tuc` cat manh
nhat (con 6,5%, dung bang 0,5^n) va mot minh no dua 93 lenh xuong 6.

```
```

Day la thu tra loi ngay cau "sao khong co lenh nao", va no re: cac mat na deu
da duoc tinh trong `signals()`.

## Xu ly loi

| tinh huong | xu ly |
|---|---|
| Symbol khong ton tai tren Binance | `POST /api/run` tra 400 kem thong bao; kiem bang `/fapi/v1/exchangeInfo` truoc khi tao job |
| Tai bi ngat giua chung | Cac file CSV theo ngay da cache rieng le -> chay lai la tiep tuc, khong tai lai tu dau |
| Nguoi dung bam Huy | Job dat co huy; vong tai kiem co moi 20 ngay roi dung; cache tung phan giu lai |
| Kho metrics thieu du lieu | Da xu ly san: o trong -> NaN -> nen do khong co tin hieu (do duoc: OI thieu 2,23%, taker 8,92%) |
| Hai tab cung chay mot config | Job theo `key`; tab thu hai gan vao job dang chay thay vi tao job moi |
| Config cho 0 lenh | Hien pheu dieu kien (tren) |

## Kiem thu

**Test golden — quan trong nhat.** Voi `BTCUSDT / 1h / n=3 / wick=10% / 2100
ngay`, `/api/result` phai tra ve dung so lenh va dung `R gop`, `bps rong` ma
`scripts/bt_rule_extreme.py` in ra. Test nay ghim duong web vao duong Python da
kiem chung; thieu no thi khong con biet con so tren man hinh nghia la gi.

**Test khoa cache.** Doi `RULE_VERSION` phai sinh khoa khac. Doi bat ky truong
config nao phai sinh khoa khac. Hai config giong nhau phai sinh khoa giong nhau.

**Test lat nen.** `bars` cua moi lenh phai trung voi 6 nen tuong ung cua chuoi
chinh tai cung timeframe — de bat loi lech mot nen giua "nen tin hieu" va "nen
vao lenh".

**Test sua lenh.** `PUT` voi dung TP/SL goc phai tra ve dung `r` va `bps` goc.
Neu khong, ham tinh lai va ham tinh ban dau da troi khoi nhau.

**Test lazy-load.** 1.000 the, cuon het: so phan tu DOM khong vuot 3x so the
dang hien.

## Quyet dinh da chot

- **Do sau lich su la mot o config** (mac dinh 365 ngay ~2 phut cho symbol moi;
  1.095 va 2.100 ngay la tuy chon). Symbol tai theo yeu cau, khong dung san
  danh sach.
- **`RULE_VERSION` la hang so trong `rules.py`**, tang moi khi dinh nghia tin
  hieu doi. Khong co no, sua luat xong cache cu van duoc phuc vu.
- **Server chi nghe 127.0.0.1.** Mo ra mang la quyet dinh cua nguoi dung, khong
  phai mac dinh.
