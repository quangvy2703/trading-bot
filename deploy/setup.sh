#!/bin/sh
# Chay MOT LAN tren may chu Ubuntu 24.04 moi, TRUOC khi chuyen bot sang:
#   gcloud compute scp deploy/setup.sh deploy/backup.sh bot:~/ --zone=... --tunnel-through-iap
#   sudo sh ~/setup.sh
# Cai Docker tu kho Ubuntu, 2 GB swap (dem cho luc build + backtest), gio UTC,
# va backup DB moi ngay 01:00 UTC vao /opt/bot-backup.
set -eu

[ "$(id -u)" = 0 ] || { echo "chay bang sudo"; exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd)
USER_NAME=${SUDO_USER:?chay bang sudo tu user thuong}

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2 unattended-upgrades
systemctl enable --now docker
usermod -aG docker "$USER_NAME"
timedatectl set-timezone UTC

if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

install -m 755 "$HERE/backup.sh" /usr/local/bin/bot-backup
echo "0 1 * * * root /usr/local/bin/bot-backup >> /var/log/bot-backup.log 2>&1" \
  > /etc/cron.d/bot-backup

echo "xong. thoat SSH roi vao lai de nhom docker co hieu luc."
