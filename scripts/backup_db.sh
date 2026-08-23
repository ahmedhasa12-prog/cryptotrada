#!/bin/bash
# Safe hot backup — works while the server is running (SQLite .backup API is crash-safe)

DB="/Users/ahmedabdelwahid/projects/cryptotrada/data/trading.db"
BACKUP_DIR="/Users/ahmedabdelwahid/projects/cryptotrada/backups"
STAMP=$(date +%Y-%m-%d)
DEST="$BACKUP_DIR/trading_$STAMP.db"

# Skip if today's backup already exists
if [ -f "$DEST" ]; then
  exit 0
fi

sqlite3 "$DB" ".backup '$DEST'"

# Keep last 14 days only
find "$BACKUP_DIR" -name "trading_*.db" -mtime +14 -delete

echo "$(date '+%Y-%m-%d %H:%M:%S') — backup written to $DEST"
