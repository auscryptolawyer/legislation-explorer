#!/bin/bash
# Legislation Explorer — Daily backup script
# Backs up data/ and search_index.db to timestamped archives.
# Keeps 30 days of backups.

set -euo pipefail

PROJECT="/home/harrison/legislation-explorer"
BACKUP_DIR="/home/harrison/backups/legislation-explorer"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE="${BACKUP_DIR}/le_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date -Iseconds)] Starting backup..."

# Create tarball with data/ and search_index.db
tar -czf "$ARCHIVE" \
    -C "$PROJECT" \
    data \
    search_index.db

SIZE=$(du -h "$ARCHIVE" | cut -f1)
echo "[$(date -Iseconds)] Backup complete: ${ARCHIVE} (${SIZE})"

# Purge backups older than 30 days
DELETED=$(find "$BACKUP_DIR" -name 'le_*.tar.gz' -mtime +30 -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$(date -Iseconds)] Purged ${DELETED} backups older than 30 days"
fi

# Report disk usage
USED=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "[$(date -Iseconds)] Backup dir usage: ${USED}"
