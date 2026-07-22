#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

if [[ ! -f .env ]]; then
  echo "Missing deploy/oracle/.env" >&2
  exit 1
fi

set -a
source .env
set +a

backup_dir="$script_dir/backups"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/whichmovie-$timestamp.dump"

mkdir -p "$backup_dir"

docker compose exec -T db pg_dump \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --format custom \
  --compress 9 \
  > "$backup_file"

echo "Created $backup_file"

if [[ -n "${OCI_BUCKET_NAME:-}" ]]; then
  if ! command -v oci >/dev/null 2>&1; then
    echo "OCI_BUCKET_NAME is set, but the OCI CLI is not installed." >&2
    exit 1
  fi

  oci os object put \
    --bucket-name "$OCI_BUCKET_NAME" \
    --file "$backup_file" \
    --name "$(basename "$backup_file")" \
    --force

  echo "Uploaded $(basename "$backup_file") to $OCI_BUCKET_NAME"
fi

find "$backup_dir" \
  -type f \
  -name 'whichmovie-*.dump' \
  -mtime +7 \
  -delete
