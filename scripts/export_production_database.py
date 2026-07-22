import argparse
from pathlib import Path
import subprocess


default_container = "whichmovie-postgres"
default_database = "whichmovie"
default_user = "postgres"
default_output = Path("data/processed/whichmovie-production.dump")
default_max_size_mb = 450

production_tables = (
    "movies",
    "movie_external_ids",
    "movie_memory_clues",
)

excluded_table_data = (
    "public.movie_search_documents",
    "public.movie_search_document_embeddings",
)


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )


def get_production_size_bytes(
    container: str,
    database: str,
    user: str,
) -> int:
    table_names = ", ".join(f"'{table}'" for table in production_tables)
    sql = f"""
        select coalesce(sum(pg_total_relation_size(quote_ident(tablename))), 0)
        from pg_tables
        where schemaname = 'public'
          and tablename in ({table_names});
    """
    result = run_command(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            user,
            "-d",
            database,
            "-AtX",
            "-c",
            sql,
        ]
    )
    return int(result.stdout.strip())


def export_database(
    container: str,
    database: str,
    user: str,
    output_path: Path,
) -> None:
    command = [
        "docker",
        "exec",
        container,
        "pg_dump",
        "-U",
        user,
        "-d",
        database,
        "-Fc",
        "--no-owner",
        "--no-privileges",
    ]

    for table in excluded_table_data:
        command.append(f"--exclude-table-data={table}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("wb") as output_file:
        result = subprocess.run(
            command,
            stdout=output_file,
            stderr=subprocess.PIPE,
            check=False,
        )

    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        error = result.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"pg_dump failed: {error.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Export the production database while keeping experimental "
            "document tables empty."
        )
    )
    parser.add_argument("--container", default=default_container)
    parser.add_argument("--database", default=default_database)
    parser.add_argument("--user", default=default_user)
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--max-size-mb", type=int, default=default_max_size_mb)
    args = parser.parse_args()

    production_size_bytes = get_production_size_bytes(
        container=args.container,
        database=args.database,
        user=args.user,
    )
    production_size_mb = production_size_bytes / (1024 * 1024)

    print(f"production table size: {production_size_mb:.1f} MB")
    print(f"free database limit guard: {args.max_size_mb} MB")

    if production_size_mb > args.max_size_mb:
        raise RuntimeError(
            "production tables exceed the configured free database limit"
        )

    output_path = args.output.resolve()
    export_database(
        container=args.container,
        database=args.database,
        user=args.user,
        output_path=output_path,
    )

    dump_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"production dump: {output_path}")
    print(f"compressed dump size: {dump_size_mb:.1f} MB")
    print("document table schemas kept; document table data excluded")


if __name__ == "__main__":
    main()
