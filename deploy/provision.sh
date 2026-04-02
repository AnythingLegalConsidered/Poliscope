#!/usr/bin/env bash
# provision.sh — One-time LXC setup for Poliscope
# Run as root on the LXC: bash provision.sh
# Idempotent — safe to re-run.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

step() { echo -e "${CYAN}==> $1${NC}"; }
ok()   { echo -e "${GREEN}    OK: $1${NC}"; }

# ---------------------------------------------------------------------------
# Step 1: Install Node.js 22 LTS via NodeSource
# ---------------------------------------------------------------------------
step "Installing Node.js 22 LTS via NodeSource..."
if node --version 2>/dev/null | grep -q '^v22'; then
  ok "Node.js 22 already installed: $(node --version)"
else
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
  ok "Node.js installed: $(node --version)"
fi

# ---------------------------------------------------------------------------
# Step 2: Install PM2 globally
# ---------------------------------------------------------------------------
step "Installing PM2 globally..."
if pm2 --version &>/dev/null; then
  ok "PM2 already installed: $(pm2 --version)"
else
  npm install -g pm2
  ok "PM2 installed: $(pm2 --version)"
fi

# ---------------------------------------------------------------------------
# Step 3: Install nginx
# ---------------------------------------------------------------------------
step "Installing nginx..."
apt-get install -y nginx
ok "nginx installed: $(nginx -v 2>&1)"

# ---------------------------------------------------------------------------
# Step 4: Create directory structure
# ---------------------------------------------------------------------------
step "Creating /opt/poliscope directory structure..."
mkdir -p /opt/poliscope/{.output,repo,backups,logs,scripts}
chown -R root:root /opt/poliscope
# backups must be writable by postgres user for pg_dump
mkdir -p /opt/poliscope/backups
chown postgres:postgres /opt/poliscope/backups
ok "Directories created"

# ---------------------------------------------------------------------------
# Step 5: Open UFW port 80/tcp
# ---------------------------------------------------------------------------
step "Configuring UFW — opening port 80/tcp..."
if ufw status | grep -q "80/tcp"; then
  ok "UFW port 80/tcp already open"
else
  ufw allow 80/tcp
  ok "UFW port 80/tcp opened"
fi

# ---------------------------------------------------------------------------
# Step 6: Remove default nginx site
# ---------------------------------------------------------------------------
step "Removing default nginx site..."
rm -f /etc/nginx/sites-enabled/default
ok "Default nginx site removed (if it existed)"

# ---------------------------------------------------------------------------
# Step 7: Deploy nginx config for Poliscope
# ---------------------------------------------------------------------------
step "Deploying nginx config..."
NGINX_CONF_SRC="/opt/poliscope/repo/deploy/nginx/poliscope.conf"
NGINX_CONF_DEST="/etc/nginx/sites-available/poliscope"
NGINX_CONF_LINK="/etc/nginx/sites-enabled/poliscope"

if [ -f "$NGINX_CONF_SRC" ]; then
  cp "$NGINX_CONF_SRC" "$NGINX_CONF_DEST"
  ln -sf "$NGINX_CONF_DEST" "$NGINX_CONF_LINK"
  ok "nginx config deployed from repo"
else
  echo -e "${RED}    WARNING: $NGINX_CONF_SRC not found — run this script after cloning the repo to /opt/poliscope/repo${NC}"
  echo -e "${RED}    Skip nginx config step. Re-run provision.sh after cloning.${NC}"
fi

# ---------------------------------------------------------------------------
# Step 8: Test and enable nginx
# ---------------------------------------------------------------------------
step "Testing nginx config and enabling service..."
nginx -t
systemctl enable --now nginx
ok "nginx enabled and running"

# ---------------------------------------------------------------------------
# Step 9: Setup PM2 systemd startup
# ---------------------------------------------------------------------------
step "Setting up PM2 systemd startup..."
pm2 startup systemd -u root --hp /root | tail -1 | bash || true
pm2 save
ok "PM2 startup configured"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}===========================================================${NC}"
echo -e "${GREEN}  Poliscope LXC provisioning complete!${NC}"
echo -e "${GREEN}===========================================================${NC}"
echo ""
echo "  Node.js : $(node --version)"
echo "  PM2     : $(pm2 --version)"
echo "  nginx   : $(nginx -v 2>&1)"
echo "  UFW 80  : $(ufw status | grep '80/tcp' || echo 'check manually')"
echo ""
echo "  Next steps:"
echo "  1. Clone repo:  git clone <repo-url> /opt/poliscope/repo"
echo "  2. Copy .env:   scp .env root@<lxc>:/opt/poliscope/.env"
echo "  3. Run deploy:  bash deploy/deploy.sh  (from local dev machine)"
echo ""
