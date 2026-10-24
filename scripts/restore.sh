#!/bin/sh
# Restore a backup into an EMPTY database:  scripts/restore.sh db-2026....dump files-2026....tgz
set -eu
: "${DATABASE_URL:?set DATABASE_URL}"; STORAGE_DIR="${STORAGE_DIR:-./storage}"
pg_restore --no-owner --dbname "$(echo "$DATABASE_URL" | sed 's/+psycopg//')" "$1"
if [ "${2:-}" ]; then mkdir -p "$STORAGE_DIR"; tar -xzf "$2" -C "$STORAGE_DIR"; fi
echo "restored. Run 'alembic upgrade head' to make sure the schema is current."
