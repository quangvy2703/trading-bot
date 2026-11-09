#!/bin/sh
# Backup live.db bang sqlite3 backup API (an toan khi app dang ghi, khong
# can dung bot). Giu 14 ban o /opt/bot-backup. Ban sao nay nam CUNG o dia
# voi may -- mat may thi dua vao lich snapshot o dia cua GCP.
set -eu

OUT=/opt/bot-backup
mkdir -p "$OUT"
f="$OUT/live-$(date -u +%Y%m%d).db"

docker exec crypto-live python -c "
import sqlite3
s = sqlite3.connect('/data/live.db'); d = sqlite3.connect('/data/backup.db')
s.backup(d); d.close(); s.close()"
docker cp crypto-live:/data/backup.db "$f"
docker exec crypto-live rm -f /data/backup.db
gzip -f "$f"
find "$OUT" -name 'live-*.db.gz' -mtime +14 -delete
echo "$(date -u +%FT%TZ) ok $f.gz"

# So cua tung bot user (app/users.py) — vi the that cua ho nam trong cac kho nay.
for u in $(docker exec crypto-live sh -c 'ls /data/users/ 2>/dev/null | grep -E "^u[0-9]+\.db$"'); do
  g="$OUT/${u%.db}-$(date -u +%Y%m%d).db"
  docker exec crypto-live python -c "
import sqlite3
s = sqlite3.connect('/data/users/$u'); d = sqlite3.connect('/data/backup-$u')
s.backup(d); d.close(); s.close()"
  docker cp "crypto-live:/data/backup-$u" "$g"
  docker exec crypto-live rm -f "/data/backup-$u"
  gzip -f "$g"
  echo "$(date -u +%FT%TZ) ok $g.gz"
done
find "$OUT" -name 'u*-*.db.gz' -mtime +14 -delete
