#!/usr/bin/env bash
set -euo pipefail
BASE="${SMOKE_BASE_URL:-http://localhost:8000}"
API="${BASE}/api/v1"
EMAIL="${SMOKE_EMAIL:-admin@localhost}"
PASS="${SMOKE_PASSWORD:-changeme}"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

echo "== health"
curl -sf "${BASE}/health" | grep -q '"status"'

echo "== login"
curl -sf -c "$COOKIE_JAR" -X POST "${API}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASS}\"}" | grep -q '"email"'

echo "== governance run"
curl -sf -b "$COOKIE_JAR" -X POST "${API}/governance/run" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Smoke test: is release safe?"}' | grep -q '"consensus"'

echo "SMOKE OK"
