#!/usr/bin/env bash
# deploy.sh — Repeatable deploy script for Poliscope
# Run from the repo root on your local dev machine:
#   bash deploy/deploy.sh
#   bash deploy/deploy.sh --skip-build
#
# Prerequisites:
#   - SSH access to LXC: ssh root@192.168.2.200
#   - deploy/.env.production filled in (copy from deploy/.env.production.example)
#   - pnpm installed locally

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
LXC_HOST="root@192.168.2.200"
REMOTE_DIR="/opt/poliscope"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

step()    { echo -e "${CYAN}==> $1${NC}"; }
ok()      { echo -e "${GREEN}    OK: $1${NC}"; }
warn()    { echo -e "${YELLOW}    WARN: $1${NC}"; }
fail()    { echo -e "${RED}    ERROR: $1${NC}"; exit 1; }

SKIP_BUILD=false
for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Step 0: Ensure we are at repo root
# ---------------------------------------------------------------------------
if [ ! -f "pnpm-workspace.yaml" ]; then
  fail "Run this script from the repo root (where pnpm-workspace.yaml is located)"
fi

# ---------------------------------------------------------------------------
# Step 1: Create .env.production if it doesn't exist
# ---------------------------------------------------------------------------
step "Checking deploy/.env.production..."
if [ ! -f "deploy/.env.production" ]; then
  warn "deploy/.env.production not found — creating from example template"
  cp deploy/.env.production.example deploy/.env.production
  echo ""
  echo -e "${YELLOW}  ACTION REQUIRED: Edit deploy/.env.production and set NUXT_DATABASE_URL, then re-run.${NC}"
  echo ""
  exit 1
fi
ok "deploy/.env.production found"

# ---------------------------------------------------------------------------
# Step 2: Build Nuxt app (unless --skip-build)
# ---------------------------------------------------------------------------
if [ "$SKIP_BUILD" = true ]; then
  warn "Skipping build (--skip-build flag set)"
else
  step "Building Nuxt app (pnpm --filter web build)..."
  pnpm --filter web build
  ok "Build complete"
fi

if [ ! -d "packages/web/.output" ]; then
  fail "packages/web/.output not found — build may have failed or was skipped"
fi

# ---------------------------------------------------------------------------
# Step 3: Rsync .output to LXC
# ---------------------------------------------------------------------------
step "Syncing .output to ${LXC_HOST}:${REMOTE_DIR}/.output/..."
rsync -avz --delete packages/web/.output/ "${LXC_HOST}:${REMOTE_DIR}/.output/"
ok ".output synced"

# ---------------------------------------------------------------------------
# Step 4: Rsync .env.production to LXC as .env
# ---------------------------------------------------------------------------
step "Uploading .env.production to ${LXC_HOST}:${REMOTE_DIR}/.env..."
rsync -avz deploy/.env.production "${LXC_HOST}:${REMOTE_DIR}/.env"
ok ".env uploaded"

# ---------------------------------------------------------------------------
# Step 5: Rsync ecosystem.config.cjs to LXC
# ---------------------------------------------------------------------------
step "Uploading ecosystem.config.cjs to ${LXC_HOST}:${REMOTE_DIR}/..."
rsync -avz deploy/ecosystem.config.cjs "${LXC_HOST}:${REMOTE_DIR}/ecosystem.config.cjs"
ok "ecosystem.config.cjs uploaded"

# ---------------------------------------------------------------------------
# Step 6: Restart app via PM2 on LXC
# ---------------------------------------------------------------------------
step "Restarting PM2 app on LXC..."
ssh "${LXC_HOST}" "cd ${REMOTE_DIR} && pm2 startOrRestart ecosystem.config.cjs --env production && pm2 save"
ok "PM2 restarted and saved"

# ---------------------------------------------------------------------------
# Step 7: Smoke test — verify health endpoint
# ---------------------------------------------------------------------------
step "Verifying health endpoint (http://192.168.2.200/api/health)..."
sleep 2  # give Node a moment to start
HEALTH_RESPONSE=$(curl -sf "http://192.168.2.200/api/health" 2>/dev/null || echo "FAILED")

if echo "$HEALTH_RESPONSE" | grep -q '"status"'; then
  ok "Health endpoint OK: $HEALTH_RESPONSE"
else
  warn "Health endpoint returned unexpected response: $HEALTH_RESPONSE"
  warn "Check PM2 logs on LXC: ssh ${LXC_HOST} pm2 logs poliscope --lines 20"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}===========================================================${NC}"
echo -e "${GREEN}  Poliscope deploy complete!${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo ""
echo "  App URL  : http://192.168.2.200"
echo "  Health   : http://192.168.2.200/api/health"
echo "  PM2 logs : ssh ${LXC_HOST} 'pm2 logs poliscope --lines 20'"
echo ""
