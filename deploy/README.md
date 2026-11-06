# Chuyển bot lên Google Cloud (Tokyo) + Cloudflare

Máy: `n2d-standard-2` (2 vCPU AMD / 8 GB), vùng `asia-northeast1`. Trang UI không
mở cổng nào: đi qua Cloudflare Tunnel, đăng nhập bằng Cloudflare Access (OTP email).

## 1. Tài khoản GCP

1. https://console.cloud.google.com → đăng ký, thêm thẻ → nhận 300 USD / 90 ngày.
2. Tạo project (vd `crypto-bot`).
3. Billing → **Budgets & alerts** → ngân sách 80 USD/tháng, báo ở 50/90/100 %.
4. Trước khi hết 90 ngày: **Activate full account**. Không làm thì máy bị TẮT khi hết
   thử (credit còn dư vẫn giữ khi nâng cấp).

## 2. Tạo máy (trên Mac)

```sh
brew install --cask google-cloud-sdk
gcloud init                                   # chọn project vừa tạo
gcloud services enable compute.googleapis.com iap.googleapis.com

R=asia-northeast1; Z=asia-northeast1-b
gcloud compute addresses create bot-ip --region=$R
gcloud compute instances create bot --zone=$Z --machine-type=n2d-standard-2 \
  --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB --boot-disk-type=pd-balanced --address=bot-ip

# Đóng SSH/RDP mở ra Internet, chỉ cho SSH qua IAP của Google
gcloud compute firewall-rules delete default-allow-ssh default-allow-rdp --quiet
gcloud compute firewall-rules create allow-iap-ssh --network=default \
  --direction=INGRESS --allow=tcp:22 --source-ranges=35.235.240.0/20

# Snapshot ổ đĩa mỗi ngày, giữ 7 ngày
gcloud compute resource-policies create snapshot-schedule bot-daily --region=$R \
  --daily-schedule --start-time=02:00 --max-retention-days=7
gcloud compute disks add-resource-policies bot --zone=$Z --resource-policies=bot-daily

gcloud compute addresses describe bot-ip --region=$R --format='value(address)'  # IP tĩnh
```

## 3. Cài máy chủ

```sh
gcloud compute scp deploy/setup.sh deploy/backup.sh bot:~/ --zone=$Z --tunnel-through-iap
gcloud compute ssh bot --zone=$Z --tunnel-through-iap --command 'sudo sh ~/setup.sh'
```

## 4. Domain + Cloudflare

1. https://dash.cloudflare.com → **Domain Registration → Register Domains** → mua tên.
2. **Zero Trust** → chọn tên team → gói **Free** (≤ 50 người; có thể hỏi thẻ).
3. **Làm Access TRƯỚC Tunnel** (để trang không bao giờ lộ không khoá):
   Access → Applications → Add → **Self-hosted** → domain `bot.<tên-miền>` →
   Policy *Allow*, Include → **Emails** → điền email từng người. Đăng nhập mặc định
   là One-time PIN.
4. Networks → **Tunnels** → Create → Cloudflared → tên `bot` → chọn Docker → chép
   chuỗi sau `--token`. Public Hostname: `bot` . `<tên-miền>` → Service
   **HTTP** `app:8000`.

## 5. Khoá Binance mới

API Management → tạo khoá → bật Futures, **không** bật rút tiền → *Restrict access
to trusted IPs only* → IP tĩnh ở bước 2.

## 6. Chuyển bot (bot local DỪNG ở bước này)

Tránh 06:45–07:15 giờ VN (lượt 00:05 UTC).

```sh
sh deploy/migrate.sh bot $Z
gcloud compute ssh bot --zone=$Z --tunnel-through-iap
cd ~/bot/trading-bot
nano .env          # BINANCE_API_KEY, BINANCE_API_SECRET (khoá mới),
                   # NEWS_API_KEY/SECRET nếu có, TUNNEL_TOKEN=<chuỗi bước 4>
chmod 600 .env
docker compose -f docker-compose.yml -f deploy/compose.server.yml up -d --build
docker ps                                   # crypto-live (healthy) + crypto-tunnel
curl -fsS localhost:8777/healthz
```

Mở `https://bot.<tên-miền>` → nhận mã OTP → kiểm vị thế đang mở khớp với sàn.

## 7. Dọn

- Mac: **đừng** chạy lại bot local. `docker compose down` (giữ volume làm bản lưu).
- Binance: xoá khoá API cũ của máy local.
- Cập nhật code sau này: chạy lại phần đóng gói code trong `migrate.sh` hoặc `git pull`,
  rồi `docker compose -f docker-compose.yml -f deploy/compose.server.yml up -d --build`.
- Backup: `/opt/bot-backup` (01:00 UTC, giữ 14 bản) + snapshot ổ đĩa (giữ 7 ngày).
