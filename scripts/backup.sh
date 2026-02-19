#!/bin/bash
# ═══════════════════════════════════════════════════════════
# GRC Platform — Database Backup & Recovery Script
# ═══════════════════════════════════════════════════════════
# Usage:
#   ./scripts/backup.sh                     # Create backup
#   ./scripts/backup.sh restore <file>      # Restore from backup
#   ./scripts/backup.sh list                # List available backups
#   ./scripts/backup.sh cleanup             # Remove backups older than RETENTION_DAYS
#
# Environment variables (or defaults):
#   POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_SERVER
#   BACKUP_DIR          — Where to store backups (default: ./backups)
#   RETENTION_DAYS      — Days to keep backups (default: 30)
#   S3_BACKUP_BUCKET    — S3 bucket for offsite backups (optional)
# ═══════════════════════════════════════════════════════════

set -euo pipefail

# ── Config ─────────────────────────────────────────────────
POSTGRES_USER="${POSTGRES_USER:-grc_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-grc_secret}"
POSTGRES_DB="${POSTGRES_DB:-grc_db}"
POSTGRES_SERVER="${POSTGRES_SERVER:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BACKUP_BUCKET="${S3_BACKUP_BUCKET:-}"

export PGPASSWORD="$POSTGRES_PASSWORD"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

# ── Functions ──────────────────────────────────────────────

do_backup() {
    echo "🔄 Starting backup of database: $POSTGRES_DB"
    echo "   Host: $POSTGRES_SERVER:$POSTGRES_PORT"
    echo "   Destination: $BACKUP_FILE"

    pg_dump \
        -h "$POSTGRES_SERVER" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --format=custom \
        --compress=9 \
        --verbose \
        2>/dev/null | gzip > "$BACKUP_FILE"

    FILESIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup complete: $BACKUP_FILE ($FILESIZE)"

    # Optional: Upload to S3
    if [ -n "$S3_BACKUP_BUCKET" ]; then
        echo "☁️  Uploading to S3: s3://$S3_BACKUP_BUCKET/backups/"
        aws s3 cp "$BACKUP_FILE" "s3://$S3_BACKUP_BUCKET/backups/" --quiet
        echo "✅ S3 upload complete."
    fi
}

do_restore() {
    local RESTORE_FILE="$1"
    if [ ! -f "$RESTORE_FILE" ]; then
        echo "❌ Backup file not found: $RESTORE_FILE"
        exit 1
    fi

    echo "⚠️  WARNING: This will overwrite database '$POSTGRES_DB'!"
    echo "   Restoring from: $RESTORE_FILE"
    read -p "   Continue? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi

    echo "🔄 Restoring..."
    gunzip -c "$RESTORE_FILE" | pg_restore \
        -h "$POSTGRES_SERVER" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --clean \
        --if-exists \
        --verbose \
        2>/dev/null

    echo "✅ Restore complete."
}

do_list() {
    echo "📂 Available backups in $BACKUP_DIR:"
    echo "───────────────────────────────────────"
    if [ -d "$BACKUP_DIR" ] && [ "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
        ls -lhS "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No .sql.gz files found."
    else
        echo "No backups found."
    fi
}

do_cleanup() {
    echo "🧹 Removing backups older than $RETENTION_DAYS days..."
    DELETED=$(find "$BACKUP_DIR" -name "*.sql.gz" -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
    echo "✅ Removed $DELETED old backup(s)."
}

# ── Main ───────────────────────────────────────────────────

ACTION="${1:-backup}"

case "$ACTION" in
    backup)
        do_backup
        ;;
    restore)
        if [ -z "${2:-}" ]; then
            echo "Usage: $0 restore <backup_file>"
            exit 1
        fi
        do_restore "$2"
        ;;
    list)
        do_list
        ;;
    cleanup)
        do_cleanup
        ;;
    *)
        echo "Usage: $0 {backup|restore|list|cleanup} [args]"
        exit 1
        ;;
esac
