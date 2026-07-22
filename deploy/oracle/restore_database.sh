#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: ./restore_database.sh /path/to/whichmovie.dump" >&2
  exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
backup_file="$(realpath "$1")"
cd "$script_dir"

if [[ ! -f .env ]]; then
  echo "Missing deploy/oracle/.env" >&2
  exit 1
fi

if [[ ! -f "$backup_file" ]]; then
  echo "Backup does not exist: $backup_file" >&2
  exit 1
fi

set -a
source .env
set +a

docker compose exec -T db pg_restore \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --clean \
  --if-exists \
  --no-owner \
  < "$backup_file"

echo "Restored $backup_file"
