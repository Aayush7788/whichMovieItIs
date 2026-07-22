import argparse
import os
from pathlib import Path
import subprocess


default_image = "pgvector/pgvector:0.8.2-pg17"


def run_database_command(
    database_url: str,
    mount: str,
    image: str,
    command: str,
    network: str | None = None,
) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url

    docker_command = [
        "docker",
        "run",
        "--rm",
        "-e",
        "DATABASE_URL",
    ]

    if network:
        docker_command.extend(["--network", network])

    docker_command.extend(
        [
            "-v",
            mount,
            image,
            "sh",
            "-c",
            command,
        ]
    )

    return subprocess.run(
        docker_command,
        check=True,
        env=environment,
        text=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore the compact production dump to PostgreSQL."
    )
    parser.add_argument("dump", type=Path)
    parser.add_argument(
        "--database-url",
        default=os.getenv("NEON_DATABASE_URL"),
    )
    parser.add_argument("--image", default=default_image)
    parser.add_argument(
        "--network",
        help="Optional Docker network used for local restore testing.",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise RuntimeError("set NEON_DATABASE_URL or pass --database-url")

    dump_path = args.dump.resolve()

    if not dump_path.is_file():
        raise FileNotFoundError(f"dump not found: {dump_path}")

    mount = f"{dump_path.parent}:/backup:ro"
    remote_dump = f"/backup/{dump_path.name}"

    print("enabling pgvector extension")
    run_database_command(
        database_url=args.database_url,
        mount=mount,
        image=args.image,
        network=args.network,
        command=(
            'psql "$DATABASE_URL" -v ON_ERROR_STOP=1 '
            "-c 'create extension if not exists vector;'"
        ),
    )

    print("restoring production database")
    run_database_command(
        database_url=args.database_url,
        mount=mount,
        image=args.image,
        network=args.network,
        command=(
            f'pg_restore --dbname="$DATABASE_URL" '
            "--clean --if-exists --no-owner --no-privileges "
            f"--exit-on-error {remote_dump}"
        ),
    )

    print("verifying restored database")
    run_database_command(
        database_url=args.database_url,
        mount=mount,
        image=args.image,
        network=args.network,
        command=(
            'psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "'
            "select count(*) as movies from movies; "
            "select pg_size_pretty(pg_database_size(current_database())) "
            'as database_size;"'
        ),
    )


if __name__ == "__main__":
    main()
