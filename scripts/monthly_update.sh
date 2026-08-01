#!/bin/bash
set -euo pipefail
cd /home/harrison/legislation-explorer
PY=backend/venv/bin/python
LOG="/home/harrison/logs/monthly_update_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG")"
$PY scripts/monthly_update.py 2>&1 | tee "$LOG"
