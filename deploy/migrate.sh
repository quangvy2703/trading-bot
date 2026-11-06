#!/bin/sh
# Chay TREN MAC: dung bot local, chep code + so lenh (volume live2_livedata)
# len may chu GCP. Hai bot KHONG duoc chay cung luc -- ca hai se dat lenh
# tren cung tai khoan.
#
#   sh deploy/migrate.sh bot asia-northeast1-b
set -eu

VM=${1:?ten may, vd bot}
ZONE=${2:?zone, vd asia-northeast1-b}
DIR=$(cd "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
SSH="gcloud compute ssh $VM --zone=$ZONE --tunnel-through-iap"
SCP="gcloud compute scp --zone=$ZONE --tunnel-through-iap"

echo "== dung bot local"
(cd "$DIR" && docker compose stop app)

echo "== dong goi volume + code"
docker run --rm -v live2_livedata:/data -v "$TMP":/out alpine \
  tar czf /out/livedata.tgz -C /data .
COPYFILE_DISABLE=1 tar czf "$TMP/code.tgz" --no-mac-metadata -C "$DIR/.." \
  --exclude=.env --exclude=__pycache__ --exclude='*.db' "$(basename "$DIR")"

echo "== chep len $VM"
$SCP "$TMP/livedata.tgz" "$TMP/code.tgz" "$VM":~/

echo "== giai nen tren may chu"
$SSH --command '
set -e
mkdir -p ~/bot && tar xzf ~/code.tgz -C ~/bot
docker volume inspect live2_livedata >/dev/null 2>&1 && {
  echo "volume live2_livedata da co tren may chu -- dung lai, khong ghi de"; exit 1; }
# nhan giong volume do compose tao, de compose dung lai ma khong canh bao
docker volume create --label com.docker.compose.project=live \
  --label com.docker.compose.volume=livedata live2_livedata >/dev/null
docker run --rm -v live2_livedata:/data -v ~/:/in alpine tar xzf /in/livedata.tgz -C /data
rm ~/livedata.tgz ~/code.tgz
ls -la ~/bot/trading-bot'
rm -rf "$TMP"

echo "== xong. Tiep: tao ~/bot/trading-bot/.env tren may chu roi"
echo "   docker compose -f docker-compose.yml -f deploy/compose.server.yml up -d --build"
