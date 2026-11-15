#!/usr/bin/env bash
# Deploy SeaShield AI to a fresh Vultr Ubuntu 24.04 instance (run from the repo root, Git Bash).
#
#   bash infra/scripts/deploy_vultr.sh <server-ip> [domain]
#
# - ships the committed code (git archive) + data/processed/*.parquet
# - installs Docker, opens only 22/80/443 (ufw)
# - generates buoy keys and .env ON THE SERVER (secrets never leave it)
# - domain defaults to <ip-with-dashes>.sslip.io (free DNS); Caddy gets HTTPS automatically
set -euo pipefail
IP="${1:?usage: deploy_vultr.sh <server-ip> [domain]}"
DOMAIN="${2:-${IP//./-}.sslip.io}"
KEY="${SSH_KEY:-$HOME/.ssh/seashield_vultr}"
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new root@$IP"
APP=/opt/seashield

echo "==> packaging commit $(git rev-parse --short HEAD) + processed data"
TMP=$(mktemp -d)
git archive --format=tar.gz -o "$TMP/app.tar.gz" HEAD
tar -czf "$TMP/data.tar.gz" data/processed/42036.parquet data/processed/42097.parquet \
  data/processed/42099.parquet data/processed/42013.parquet models/isolation_forest.joblib

echo "==> uploading to $IP"
$SSH "mkdir -p $APP"
scp -i "$KEY" "$TMP/app.tar.gz" "$TMP/data.tar.gz" "root@$IP:$APP/"

echo "==> server setup + start ($DOMAIN)"
$SSH bash -s -- "$APP" "$DOMAIN" <<'REMOTE'
set -euo pipefail
APP="$1"; DOMAIN="$2"
cd "$APP"
tar -xzf app.tar.gz && tar -xzf data.tar.gz && rm -f app.tar.gz data.tar.gz

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
apt-get install -y -qq ufw python3-yaml >/dev/null
ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

[ -f secrets/buoy_keys.json ] || python3 infra/scripts/gen_buoy_keys.py
chmod 644 secrets/buoy_keys.json   # readable by the non-root user inside the containers

if [ ! -f .env ]; then
  PW=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")
  sed "s/change-me/$PW/g" .env.example > .env
fi
sed -i "s/^SEASHIELD_DOMAIN=.*/SEASHIELD_DOMAIN=$DOMAIN/" .env
sed -i "s/^SEASHIELD_ENV=.*/SEASHIELD_ENV=prod/" .env

docker compose up -d --build
docker compose ps
REMOTE

rm -rf "$TMP"
echo "==> done: https://$DOMAIN"
