#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/poliscope/backups"
mkdir -p "$BACKUP_DIR"

FILENAME="poliscope_$(date +%Y%m%d_%H%M%S).sql.gz"
pg_dump -d poliscope | gzip > "$BACKUP_DIR/$FILENAME"

# Retain last 30 days
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Backup complete: $(ls -lh "$BACKUP_DIR/$FILENAME")"
