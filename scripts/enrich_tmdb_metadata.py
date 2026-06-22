import argparse
import time

import httpx

from backend.app.db import get_connection
from backend.app.services.tmdb import (
    create_tmdb_client,
    search_tmdb_movie,
)


default_batch_size = 50
default_delay_ms = 100

mark_matched_sql = """
    update movies
    set tmdb_id = %(tmdb_id)s,
        poster_path = %(poster_path)s,
        metadata_source = 'tmdb',
        metadata_match_status = 'matched',
        metadata_updated_at = now()
    where id = %(movie_id)s;
"""

mark_not_found_sql = """
    update movies
    set metadata_source = 'tmdb',
        metadata_match_status = 'not_found',
        metadata_updated_at = now()
    where id = %(movie_id)s;
"""

mark_error_sql = """
    update movies
    set metadata_source = 'tmdb',
        metadata_match_status = 'error',
        metadata_updated_at = now()
    where id = %(movie_id)s;
"""


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum movies to process. Use 0 for all pending movies.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=default_batch_size,
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=default_delay_ms,
    )
    parser.add_argument(
        "--wikipedia-id",
        action="append",
        dest="wikipedia_ids",
        default=[],
    )

    return parser.parse_args()


def fetch_movies(
    cursor,
    limit: int,
    wikipedia_ids: list[str],
):
    filters = [
        "tmdb_id is null",
        "metadata_match_status is null",
    ]

    parameters: dict[str, object] = {
        "limit": limit,
    }

    if wikipedia_ids:
        filters.append(
            "wikipedia_movie_id = "
            "any(%(wikipedia_ids)s::text[])"
        )
        parameters["wikipedia_ids"] = wikipedia_ids

    query = f"""
        select
            id,
            wikipedia_movie_id,
            title,
            release_date
        from movies
        where {" and ".join(filters)}
        order by id
        limit %(limit)s;
    """

    cursor.execute(query, parameters)
    return cursor.fetchall()


def process_movies(
    cursor,
    client,
    rows,
    delay_ms: int,
    statistics: dict[str, int],
):
    for (
        movie_id,
        wikipedia_movie_id,
        title,
        release_date,
    ) in rows:
        try:
            match = search_tmdb_movie(
                client=client,
                title=title,
                release_date=release_date,
            )
        except (
            httpx.HTTPError,
            RuntimeError,
            ValueError,
        ) as error:
            cursor.execute(
                mark_error_sql,
                {"movie_id": movie_id},
            )

            statistics["error"] += 1

            print(
                f"error: {wikipedia_movie_id} "
                f"{title}: {error}"
            )
        else:
            if match is None:
                cursor.execute(
                    mark_not_found_sql,
                    {"movie_id": movie_id},
                )

                statistics["not_found"] += 1

                print(
                    f"not found: "
                    f"{wikipedia_movie_id} {title}"
                )
            else:
                cursor.execute(
                    mark_matched_sql,
                    {
                        "movie_id": movie_id,
                        "tmdb_id": int(match["id"]),
                        "poster_path": match.get(
                            "poster_path"
                        ),
                    },
                )

                statistics["matched"] += 1

                print(
                    f"matched: {wikipedia_movie_id} "
                    f"{title} -> {match['id']}"
                )

        statistics["processed"] += 1

        time.sleep(
            max(delay_ms, 0) / 1000
        )


def main():
    args = parse_args()

    if args.limit < 0:
        raise ValueError(
            "limit must be zero or greater"
        )

    if args.batch_size < 1:
        raise ValueError(
            "batch size must be at least one"
        )

    statistics = {
        "processed": 0,
        "matched": 0,
        "not_found": 0,
        "error": 0,
    }

    total_limit = (
        None
        if args.limit == 0
        else args.limit
    )

    with create_tmdb_client() as client:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                if args.wikipedia_ids:
                    rows = fetch_movies(
                        cursor=cursor,
                        limit=len(args.wikipedia_ids),
                        wikipedia_ids=args.wikipedia_ids,
                    )

                    process_movies(
                        cursor=cursor,
                        client=client,
                        rows=rows,
                        delay_ms=args.delay_ms,
                        statistics=statistics,
                    )

                    connection.commit()
                else:
                    while (
                        total_limit is None
                        or statistics["processed"]
                        < total_limit
                    ):
                        batch_size = args.batch_size

                        if total_limit is not None:
                            remaining = (
                                total_limit
                                - statistics["processed"]
                            )
                            batch_size = min(
                                batch_size,
                                remaining,
                            )

                        rows = fetch_movies(
                            cursor=cursor,
                            limit=batch_size,
                            wikipedia_ids=[],
                        )

                        if not rows:
                            break

                        process_movies(
                            cursor=cursor,
                            client=client,
                            rows=rows,
                            delay_ms=args.delay_ms,
                            statistics=statistics,
                        )

                        connection.commit()

    print()
    print("TMDB enrichment complete")

    for name, value in statistics.items():
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()