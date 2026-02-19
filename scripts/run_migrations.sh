#!/bin/bash
# ═══════════════════════════════════════════════════════════
# GRC Platform — Database Migration Script
# ═══════════════════════════════════════════════════════════
# Usage:
#   ./scripts/run_migrations.sh                # Run pending migrations
#   ./scripts/run_migrations.sh generate "msg" # Generate a new migration
#   ./scripts/run_migrations.sh downgrade -1   # Rollback one migration
#   ./scripts/run_migrations.sh current        # Show current revision
#   ./scripts/run_migrations.sh history        # Show migration history
# ═══════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../backend" && pwd)"

cd "$BACKEND_DIR"

ACTION="${1:-upgrade}"

case "$ACTION" in
    upgrade)
        echo "🔄 Running pending database migrations..."
        alembic upgrade head
        echo "✅ Migrations complete."
        ;;
    generate)
        MESSAGE="${2:-auto_migration}"
        echo "📝 Generating new migration: $MESSAGE"
        alembic revision --autogenerate -m "$MESSAGE"
        echo "✅ Migration file created. Review it before applying."
        ;;
    downgrade)
        TARGET="${2:--1}"
        echo "⏪ Rolling back to: $TARGET"
        alembic downgrade "$TARGET"
        echo "✅ Rollback complete."
        ;;
    current)
        echo "📌 Current database revision:"
        alembic current
        ;;
    history)
        echo "📜 Migration history:"
        alembic history --verbose
        ;;
    stamp)
        REVISION="${2:-head}"
        echo "🏷️  Stamping database at revision: $REVISION"
        alembic stamp "$REVISION"
        echo "✅ Database stamped."
        ;;
    *)
        echo "Unknown action: $ACTION"
        echo "Usage: $0 {upgrade|generate|downgrade|current|history|stamp} [args]"
        exit 1
        ;;
esac
