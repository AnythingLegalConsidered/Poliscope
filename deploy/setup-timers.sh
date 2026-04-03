#!/bin/bash
set -euo pipefail

echo "=== Setting up Poliscope systemd timers ==="

# Copy scripts
cp /opt/poliscope/repo/deploy/scripts/pg-backup.sh /opt/poliscope/scripts/pg-backup.sh
chmod +x /opt/poliscope/scripts/pg-backup.sh

# Ensure backup dir is owned by postgres
mkdir -p /opt/poliscope/backups
chown postgres:postgres /opt/poliscope/backups

# Ensure logs dir exists
mkdir -p /opt/poliscope/logs

# Copy systemd units
cp /opt/poliscope/repo/deploy/systemd/*.service /etc/systemd/system/
cp /opt/poliscope/repo/deploy/systemd/*.timer /etc/systemd/system/

# Reload and enable timers
systemctl daemon-reload
systemctl enable --now pg-backup-poliscope.timer
systemctl enable --now poliscope-refresh.timer

# Setup Python venv for ingestion (if not exists)
if [ ! -d /opt/poliscope/repo/packages/ingestion/.venv ]; then
    echo "Creating Python venv for ingestion..."
    apt-get install -y python3-venv python3-pip
    cd /opt/poliscope/repo/packages/ingestion
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

echo ""
echo "=== Timers installed ==="
systemctl list-timers --no-pager | grep poliscope
echo ""
echo "IMPORTANT: Edit /etc/systemd/system/poliscope-refresh.service"
echo "  Replace PASSWORD in DATABASE_URL with the real password"
echo "  Then: systemctl daemon-reload"
