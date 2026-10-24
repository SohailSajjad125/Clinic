#!/bin/sh
# Daily PostgreSQL + uploaded-files backup with retention. Run from cron, e.g.:  15 2 * * *  /opt/clinicos/scripts/backup.sh
# Needs: pg_dump on PATH, DATABASE_URL (libpq form: postgresql://user:pass@host/db), STORAGE_DIR, BACKUP_DIR.
set -eu
: "${DATABASE_URL:?set DATABASE_URL (postgresql://...)}"; : "${BACKUP_DIR:?set BACKUP_DIR}"; STORAGE_DIR="${STORAGE_DIR:-./storage}"; KEEP_DAYS="${KEEP_DAYS:-14}"
stamp=$(date +%Y%m%d-%H%M%S); mkdir -p "$BACKUP_DIR"
pg_dump --format=custom --no-owner "$(echo "$DATABASE_URL" | sed 's/+psycopg//')" > "$BACKUP_DIR/db-$stamp.dump"
[ -d "$STORAGE_DIR" ] && tar -czf "$BACKUP_DIR/files-$stamp.tgz" -C "$STORAGE_DIR" .
find "$BACKUP_DIR" -name 'db-*.dump' -mtime +"$KEEP_DAYS" -delete; find "$BACKUP_DIR" -name 'files-*.tgz' -mtime +"$KEEP_DAYS" -delete
echo "backup written: $BACKUP_DIR/db-$stamp.dump"
