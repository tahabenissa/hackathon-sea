#!/usr/bin/env bash
# Self-signed CA + server certificate for Mosquitto TLS (port 8883).
# Usage: bash infra/scripts/gen_certs.sh <broker-hostname>
set -euo pipefail
HOST="${1:?usage: gen_certs.sh <broker-hostname>}"
OUT="infra/mosquitto/certs"
mkdir -p "$OUT"
openssl req -x509 -newkey rsa:4096 -nodes -days 365 \
  -keyout "$OUT/ca.key" -out "$OUT/ca.crt" -subj "/CN=SeaShield CA"
openssl req -newkey rsa:2048 -nodes \
  -keyout "$OUT/server.key" -out "$OUT/server.csr" -subj "/CN=$HOST"
openssl x509 -req -in "$OUT/server.csr" -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" \
  -CAcreateserial -out "$OUT/server.crt" -days 365
chmod 600 "$OUT"/*.key
echo "Certificates written to $OUT (git-ignored)."
