import argparse

from backend.app.db import get_connection


audit_sql = """
    select
        current_setting('server_version') as postgres_version,
        (
            select extversion
            from pg_extension
            where extname = 'vector'
        ) as pgvector_version,
        pg_database_size(current_database()) as database_size_bytes,
        (select count(*) from movies) as movies,
        (
            select count(*)
            from movies
            where search_embedding is not null
        ) as movie_embeddings,
        (
            select count(*)
            from movies
            where search_embedding is null
        ) as missing_movie_embeddings,
        (
            select count(*)
            from movies
            where source = 'tmdb'
        ) as tmdb_movies,
        (
            select count(*)
            from movie_external_ids
            where source = 'tmdb'
        ) as tmdb_external_ids,
        (select count(*) from movie_search_documents) as search_documents,
        (
            select count(*)
            from movie_search_document_embeddings
        ) as document_embeddings;
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit the deployed WhichMovieItIs PostgreSQL database."
    )
    parser.add_argument("--max-size-mb", type=int, default=450)
    args = parser.parse_args()

    if args.max_size_mb < 1:
        raise ValueError("max-size-mb must be at least one")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(audit_sql)
            row = cursor.fetchone()

    if row is None:
        raise RuntimeError("database audit returned no result")

    names = (
        "postgres_version",
        "pgvector_version",
        "database_size_bytes",
        "movies",
        "movie_embeddings",
        "missing_movie_embeddings",
        "tmdb_movies",
        "tmdb_external_ids",
        "search_documents",
        "document_embeddings",
    )
    result = dict(zip(names, row))
    database_size_mb = int(result["database_size_bytes"]) / 1024 / 1024

    print(f"PostgreSQL: {result['postgres_version']}")
    print(f"pgvector: {result['pgvector_version']}")
    print(f"database size: {database_size_mb:.1f} MB")
    print(f"storage budget: {args.max_size_mb} MB")
    print(f"movies: {result['movies']}")
    print(f"movie embeddings: {result['movie_embeddings']}")
    print(
        "missing movie embeddings: "
        f"{result['missing_movie_embeddings']}"
    )
    print(f"TMDB-only movies: {result['tmdb_movies']}")
    print(f"TMDB external IDs: {result['tmdb_external_ids']}")
    print(f"search documents: {result['search_documents']}")
    print(f"document embeddings: {result['document_embeddings']}")

    failures = []

    if result["pgvector_version"] is None:
        failures.append("pgvector extension is missing")

    if int(result["movies"]) < 1:
        failures.append("movies table is empty")

    if int(result["missing_movie_embeddings"]) > 0:
        failures.append("movie embeddings are incomplete")

    if database_size_mb >= args.max_size_mb:
        failures.append("database storage budget is exhausted")

    if failures:
        raise RuntimeError("; ".join(failures))

    print("production database audit: PASS")


if __name__ == "__main__":
    main()