#!/usr/bin/env bash
# ==============================================================================
# SmartMyOdoo — Docker smoke-test (DOCKER-01 / T7)
#
# Powtarzalna weryfikacja artefaktu kontenerowego:
#   build -> up -> poll /api/status==200 -> /api/secrets==401 -> restart -> 200
#
# Mapuje na: US-DOCKER-1 (status 200), US-DOCKER-3 (secrets 401 bez tokenu),
#            US-DOCKER-2 (przeżycie restartu).
#
# Wymaga: docker + docker compose v2, plik .env z OPENROUTER_KEY.
# Użycie:  ./scripts/docker_smoke.sh            # build + up + smoke + cleanup
#          KEEP_UP=1 ./scripts/docker_smoke.sh  # zostaw kontenery po teście
#          SKIP_RESTART=1 ./scripts/docker_smoke.sh
# ==============================================================================
set -euo pipefail

# --- Konfiguracja ---
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SERVICE="${SERVICE:-app}"
MAX_WAIT="${MAX_WAIT:-120}"   # sekundy na osiągnięcie /api/status 200
KEEP_UP="${KEEP_UP:-0}"
SKIP_RESTART="${SKIP_RESTART:-0}"

# Uruchamiaj z katalogu repo (gdzie leży docker-compose.yml).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

log()  { printf '\033[1;34m[smoke]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[ OK ]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[FAIL]\033[0m %s\n' "$*" >&2; }

cleanup() {
  if [[ "${KEEP_UP}" != "1" ]]; then
    log "Sprzątanie: docker compose down (wolumeny zachowane)"
    docker compose down >/dev/null 2>&1 || true
  else
    log "KEEP_UP=1 — kontenery zostawione."
  fi
}
trap cleanup EXIT

# --- 0. Prerekwizyty ---
command -v docker >/dev/null 2>&1 || { fail "Brak 'docker' w PATH."; exit 1; }
docker compose version >/dev/null 2>&1 || { fail "Brak 'docker compose' v2."; exit 1; }
if [[ ! -f .env ]]; then
  fail "Brak pliku .env. Uruchom: cp .env.example .env i wpisz OPENROUTER_KEY."
  exit 1
fi

# --- 1. Build + up ---
log "Build obrazu i start serwisu '${SERVICE}' (z zależnościami)..."
docker compose up --build -d "${SERVICE}"

# --- 2. Poll /api/status == 200 ---
http_code() { curl -s -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || echo "000"; }

log "Czekam na ${BASE_URL}/api/status == 200 (do ${MAX_WAIT}s)..."
waited=0
until [[ "$(http_code "${BASE_URL}/api/status")" == "200" ]]; do
  if (( waited >= MAX_WAIT )); then
    fail "Timeout: /api/status nie zwrócił 200 w ${MAX_WAIT}s."
    log "Ostatnie logi serwisu:"
    docker compose logs --tail=40 "${SERVICE}" || true
    exit 1
  fi
  sleep 3
  waited=$(( waited + 3 ))
done
ok "/api/status -> 200 (po ${waited}s)"

# --- 3. /api/secrets bez tokenu == 401 ---
secrets_code="$(http_code "${BASE_URL}/api/secrets")"
if [[ "${secrets_code}" == "401" ]]; then
  ok "/api/secrets bez tokenu -> 401 (fail-closed)"
else
  fail "/api/secrets zwrócił ${secrets_code}, oczekiwano 401."
  exit 1
fi

# --- 4. (opcjonalnie) restart i ponowny status 200 (US-DOCKER-2) ---
if [[ "${SKIP_RESTART}" != "1" ]]; then
  log "Restart serwisu '${SERVICE}' (weryfikacja persystencji/odporności)..."
  docker compose restart "${SERVICE}" >/dev/null

  waited=0
  until [[ "$(http_code "${BASE_URL}/api/status")" == "200" ]]; do
    if (( waited >= MAX_WAIT )); then
      fail "Timeout: /api/status po restarcie nie zwrócił 200 w ${MAX_WAIT}s."
      exit 1
    fi
    sleep 3
    waited=$(( waited + 3 ))
  done
  ok "/api/status po restarcie -> 200 (po ${waited}s)"
fi

ok "SMOKE PASSED — kontener zdrowy (status 200, secrets 401)."
