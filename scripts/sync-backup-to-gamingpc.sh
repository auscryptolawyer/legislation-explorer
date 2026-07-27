#!/bin/bash
# Sync legislation-explorer backups to gamingpc WSL
# Uses scp for file transfer, ssh for remote management
set -euo pipefail

LOCAL_BACKUP_DIR="/home/harrison/backups/legislation-explorer"
PROJECT_DIR="/home/harrison/legislation-explorer"
SSH_HOST="gamingpc"   # must resolve via ~/.ssh/config
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "[$(date -Iseconds)] Starting gamingpc sync..."

# Ensure remote directories exist
printf 'mkdir -p ~/backups/legislation-explorer/{data,code}\n' | ssh "$SSH_HOST" 'wsl bash'

# --- 1. Latest backup tarball (search_index.db + data/) ---
LATEST_TAR=$(ls -t "$LOCAL_BACKUP_DIR"/le_*.tar.gz 2>/dev/null | head -1)
if [ -n "$LATEST_TAR" ]; then
    FNAME=$(basename "$LATEST_TAR")
    scp "$LATEST_TAR" "$SSH_HOST:C:/Users/harri/$FNAME"
    printf 'mkdir -p ~/backups/legislation-explorer/data && mv /mnt/c/Users/harri/%s ~/backups/legislation-explorer/data/%s && ls -lh ~/backups/legislation-explorer/data/%s\n' \
        "$FNAME" "$FNAME" "$FNAME" | ssh "$SSH_HOST" 'wsl bash'
else
    echo "[ERROR] No backup tarball found at $LOCAL_BACKUP_DIR"
fi

# --- 2. Full project code backup (git bundle of all branches) ---
cd "$PROJECT_DIR"
GIT_BUNDLE="legislation-explorer-${TIMESTAMP}.bundle"
git bundle create "/tmp/${GIT_BUNDLE}" --all
scp "/tmp/${GIT_BUNDLE}" "$SSH_HOST:C:/Users/harri/${GIT_BUNDLE}"
printf 'mv /mnt/c/Users/harri/%s ~/backups/legislation-explorer/code/%s && ls -lh ~/backups/legislation-explorer/code/%s\n' \
    "$GIT_BUNDLE" "$GIT_BUNDLE" "$GIT_BUNDLE" | ssh "$SSH_HOST" 'wsl bash'
rm -f "/tmp/${GIT_BUNDLE}"

echo "[$(date -Iseconds)] gamingpc sync complete."

# Show remote disk usage
printf 'echo "=== gamingpc backup sizes ===" && du -sh ~/backups/legislation-explorer/*/\n' | ssh "$SSH_HOST" 'wsl bash'
