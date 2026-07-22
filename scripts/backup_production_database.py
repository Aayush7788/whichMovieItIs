import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess

import psycopg


default_image = "postgres:18-alpine"
default_output_directory = Path("data/processed/backups")


def default_backup_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return default_output_directory / f"whichmovie-production-{timestamp}.dump"


def database_size_mb(database_url: str) -> float:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select pg_database_size(current_database());"
            )
            row = cursor.fetchone()

    if row is None:
        raise RuntimeError("database size query returned no result")

    return int(row[0]) / 1024 / 1024


def create_backup(
    database_url: str,
    output_path: Path,
    image: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path = output_path.resolve()
    mount = f"{output_path.parent}:/backup"
    remote_output = f"/backup/{output_path.name}"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url

    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-e",
            "DATABASE_URL",
            "-v",
            mount,
            image,
            "sh",
            "-c",
            (
                'pg_dump "$DATABASE_URL" --format=custom '
                "--no-owner --no-privileges "
                f"--file={remote_output}"
            ),
        ],
        check=False,
        env=environment,
        text=True,
    )

    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("production database backup failed")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a compressed backup of the Neon database."
    )
    parser.add_argument(
        "--database-url",
        default=(
            os.getenv("NEON_DIRECT_DATABASE_URL")
            or os.getenv("DATABASE_URL")
        ),
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--image", default=default_image)
    args = parser.parse_args()

    if not args.database_url:
        raise RuntimeError(
            "set NEON_DIRECT_DATABASE_URL or DATABASE_URL"
        )

    output_path = args.output or default_backup_path()
    size_mb = database_size_mb(args.database_url)
    print(f"database size before backup: {size_mb:.1f} MB")

    create_backup(
        database_url=args.database_url,
        output_path=output_path,
        image=args.image,
    )

    output_path = output_path.resolve()
    backup_size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"backup created: {output_path}")
    print(f"compressed backup size: {backup_size_mb:.1f} MB")


if __name__ == "__main__":
    main()