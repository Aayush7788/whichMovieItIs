from __future__ import annotations

import argparse
import time
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

from psycopg.types.json import Jsonb

from backend.app.config import settings
from backend.app.db import get_connection
from backend.app.services.tmdb import (
    create_tmdb_client,
    request_tmdb_json,
)


default_delay_ms = 250
default_language = "en-US"
default_minimum_overview_length = 80
default_minimum_vote_count = 25
recent_release_window_days = 365
tmdb_source = "tmdb"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--tmdb-id",
        action="append",
        type=int,
        dest="tmdb_ids",
        default=[],
    )
    parser.add_argument(
        "--source",
        choices=["manual", "discover", "changes"],
        default="manual",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--page-start",
        type=int,
        default=1,
        help="First TMDB discover page to read when --source discover is used.",
    )
    parser.add_argument(
        "--page-end",
        type=int,
        default=None,
        help="Last TMDB discover page to read when --source discover is used.",
    )
    parser.add_argument(
        "--discover-mode",
        choices=["popular", "recent"],
        default="popular",
    )
    parser.add_argument(
        "--minimum-vote-count",
        type=int,
        default=default_minimum_vote_count,
    )
    parser.add_argument(
        "--minimum-overview-length",
        type=int,
        default=default_minimum_overview_length,
    )
    parser.add_argument(
        "--release-date-from",
        default=None,
    )
    parser.add_argument(
        "--release-date-to",
        default=None,
    )
    parser.add_argument(
        "--start-date",
        default=None,
    )
    parser.add_argument(
        "--end-date",
        default=None,
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=default_delay_ms,
    )
    parser.add_argument(
        "--include-missing-overview",
        action="store_true",
    )
    parser.add_argument(
        "--max-database-size-mb",
        type=int,
        default=settings.tmdb_runtime_persistence_max_database_mb,
        help="Stop before inserting a new movie at this database size.",
    )

    return parser.parse_args()


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").split())


def list_text(values: Iterable[object]) -> str:
    cleaned_values = [
        normalize_text(value)
        for value in values
        if normalize_text(value)
    ]
    return ", ".join(cleaned_values)


def extract_genres(movie_payload: dict[str, Any]) -> list[str]:
    raw_genres = movie_payload.get("genres")

    if not isinstance(raw_genres, list):
        return []

    genres = []

    for genre in raw_genres:
        if not isinstance(genre, dict):
            continue

        name = normalize_text(genre.get("name"))

        if name:
            genres.append(name)

    return genres


def extract_keywords(movie_payload: dict[str, Any]) -> list[str]:
    keywords_payload = movie_payload.get("keywords")

    if not isinstance(keywords_payload, dict):
        return []

    raw_keywords = keywords_payload.get("keywords")

    if not isinstance(raw_keywords, list):
        return []

    keywords = []

    for keyword in raw_keywords:
        if not isinstance(keyword, dict):
            continue

        name = normalize_text(keyword.get("name"))

        if name:
            keywords.append(name)

    return keywords


def extract_cast_names(
    movie_payload: dict[str, Any],
    limit: int = 20,
) -> list[str]:
    credits_payload = movie_payload.get("credits")

    if not isinstance(credits_payload, dict):
        return []

    raw_cast = credits_payload.get("cast")

    if not isinstance(raw_cast, list):
        return []

    cast_names = []

    for cast_member in raw_cast[:limit]:
        if not isinstance(cast_member, dict):
            continue

        name = normalize_text(cast_member.get("name"))
        character = normalize_text(cast_member.get("character"))

        if name and character:
            cast_names.append(f"{name} as {character}")
        elif name:
            cast_names.append(name)

    return cast_names


def extract_crew_names(
    movie_payload: dict[str, Any],
    limit: int = 20,
) -> list[str]:
    credits_payload = movie_payload.get("credits")

    if not isinstance(credits_payload, dict):
        return []

    raw_crew = credits_payload.get("crew")

    if not isinstance(raw_crew, list):
        return []

    useful_jobs = {
        "Director",
        "Writer",
        "Screenplay",
        "Story",
        "Characters",
        "Producer",
    }

    crew_names = []

    for crew_member in raw_crew:
        if not isinstance(crew_member, dict):
            continue

        job = normalize_text(crew_member.get("job"))

        if job not in useful_jobs:
            continue

        name = normalize_text(crew_member.get("name"))

        if name:
            crew_names.append(f"{job}: {name}")

        if len(crew_names) >= limit:
            break

    return crew_names


def build_search_boost_text(movie_payload: dict[str, Any]) -> str:
    title = normalize_text(movie_payload.get("title"))
    original_title = normalize_text(movie_payload.get("original_title"))
    tagline = normalize_text(movie_payload.get("tagline"))
    overview = normalize_text(movie_payload.get("overview"))
    genres = extract_genres(movie_payload)
    keywords = extract_keywords(movie_payload)
    cast_names = extract_cast_names(movie_payload)
    crew_names = extract_crew_names(movie_payload)

    sections = [
        title,
        original_title,
        tagline,
        overview,
        f"Genres: {list_text(genres)}",
        f"Keywords: {list_text(keywords)}",
        f"Cast: {list_text(cast_names)}",
        f"Crew: {list_text(crew_names)}",
    ]

    return normalize_text(" ".join(section for section in sections if section))


def build_tmdb_documents(
    movie_payload: dict[str, Any],
) -> list[dict[str, object]]:
    tmdb_id = int(movie_payload["id"])
    title = normalize_text(movie_payload.get("title"))
    overview = normalize_text(movie_payload.get("overview"))
    tagline = normalize_text(movie_payload.get("tagline"))
    genres = extract_genres(movie_payload)
    keywords = extract_keywords(movie_payload)
    cast_names = extract_cast_names(movie_payload)
    crew_names = extract_crew_names(movie_payload)

    documents: list[dict[str, object]] = []

    if overview:
        documents.append(
            {
                "document_type": "tmdb_overview",
                "source_document_id": f"tmdb:{tmdb_id}:overview",
                "content": overview,
                "metadata": {
                    "tmdb_id": tmdb_id,
                    "title": title,
                },
            }
        )

    if tagline:
        documents.append(
            {
                "document_type": "tmdb_tagline",
                "source_document_id": f"tmdb:{tmdb_id}:tagline",
                "content": tagline,
                "metadata": {
                    "tmdb_id": tmdb_id,
                    "title": title,
                },
            }
        )

    keyword_text = list_text([*genres, *keywords])

    if keyword_text:
        documents.append(
            {
                "document_type": "tmdb_keywords",
                "source_document_id": f"tmdb:{tmdb_id}:keywords",
                "content": keyword_text,
                "metadata": {
                    "tmdb_id": tmdb_id,
                    "genres": genres,
                    "keywords": keywords,
                },
            }
        )

    credit_text = list_text([*cast_names, *crew_names])

    if credit_text:
        documents.append(
            {
                "document_type": "tmdb_credits",
                "source_document_id": f"tmdb:{tmdb_id}:credits",
                "content": credit_text,
                "metadata": {
                    "tmdb_id": tmdb_id,
                    "cast": cast_names,
                    "crew": crew_names,
                },
            }
        )

    return documents


def fetch_discover_movie_ids(
    client,
    limit: int,
    page_start: int = 1,
    page_end: int | None = None,
    discover_mode: str = "popular",
    minimum_vote_count: int = default_minimum_vote_count,
    release_date_from: str | None = None,
    release_date_to: str | None = None,
) -> list[int]:
    movie_ids: list[int] = []
    page = page_start
    release_date_to = release_date_to or date.today().isoformat()

    if discover_mode == "recent" and release_date_from is None:
        release_date_from = (
            date.today() - timedelta(days=recent_release_window_days)
        ).isoformat()

    while len(movie_ids) < limit:
        if page_end is not None and page > page_end:
            break

        params = {
            "include_adult": "false",
            "include_video": "false",
            "language": default_language,
            "page": page,
            "sort_by": (
                "primary_release_date.desc"
                if discover_mode == "recent"
                else "popularity.desc"
            ),
            "vote_count.gte": minimum_vote_count,
            "primary_release_date.lte": release_date_to,
        }

        if release_date_from:
            params["primary_release_date.gte"] = release_date_from

        payload = request_tmdb_json(
            client=client,
            path="/discover/movie",
            params=params,
        )

        results = payload.get("results")

        if not isinstance(results, list) or not results:
            break

        for result in results:
            if not isinstance(result, dict):
                continue

            tmdb_id = result.get("id")

            if isinstance(tmdb_id, int):
                movie_ids.append(tmdb_id)

            if len(movie_ids) >= limit:
                break

        total_pages = int(payload.get("total_pages") or page)

        if page >= total_pages:
            break

        page += 1

    return movie_ids


def default_changes_dates() -> tuple[str, str]:
    end_date = date.today()
    start_date = end_date - timedelta(days=1)

    return (
        start_date.isoformat(),
        end_date.isoformat(),
    )


def fetch_changed_movie_ids(
    client,
    limit: int,
    start_date: str | None,
    end_date: str | None,
) -> list[int]:
    if start_date is None or end_date is None:
        default_start_date, default_end_date = default_changes_dates()
        start_date = start_date or default_start_date
        end_date = end_date or default_end_date

    movie_ids: list[int] = []
    page = 1

    while len(movie_ids) < limit:
        payload = request_tmdb_json(
            client=client,
            path="/movie/changes",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "page": page,
            },
        )

        results = payload.get("results")

        if not isinstance(results, list) or not results:
            break

        for result in results:
            if not isinstance(result, dict):
                continue

            tmdb_id = result.get("id")

            if isinstance(tmdb_id, int):
                movie_ids.append(tmdb_id)

            if len(movie_ids) >= limit:
                break

        total_pages = int(payload.get("total_pages") or page)

        if page >= total_pages:
            break

        page += 1

    return movie_ids


def fetch_movie_details(
    client,
    tmdb_id: int,
) -> dict[str, Any]:
    payload = request_tmdb_json(
        client=client,
        path=f"/movie/{tmdb_id}",
        params={
            "append_to_response": "keywords,credits",
            "language": default_language,
        },
    )

    payload["id"] = tmdb_id

    return payload


find_movie_by_tmdb_external_id_sql = """
    select
        movie.id,
        movie.movie_key,
        movie.wikipedia_movie_id
    from movie_external_ids external_id
    join movies movie
        on movie.id = external_id.movie_id
    where external_id.source = 'tmdb'
        and external_id.external_id = %(external_id)s;
"""

find_movie_by_tmdb_id_sql = """
    select
        id,
        movie_key,
        wikipedia_movie_id
    from movies
    where tmdb_id = %(tmdb_id)s
    order by
        case
            when source = 'cmu'
            then 0
            else 1
        end,
        id
    limit 1;
"""

insert_tmdb_movie_sql = """
    insert into movies (
        movie_key,
        wikipedia_movie_id,
        freebase_movie_id,
        title,
        release_date,
        box_office_revenue,
        runtime,
        languages,
        countries,
        genres,
        plot_summary,
        source,
        tmdb_id,
        poster_path,
        metadata_source,
        metadata_match_status,
        metadata_updated_at,
        search_boost_text,
        search_embedding,
        embedding_model
    )
    values (
        %(movie_key)s,
        null,
        null,
        %(title)s,
        %(release_date)s,
        null,
        %(runtime)s,
        %(languages)s,
        %(countries)s,
        %(genres)s,
        %(plot_summary)s,
        'tmdb',
        %(tmdb_id)s,
        %(poster_path)s,
        'tmdb',
        'imported',
        now(),
        %(search_boost_text)s,
        null,
        null
    )
    on conflict (movie_key)
    do update set
        title = excluded.title,
        release_date = excluded.release_date,
        runtime = excluded.runtime,
        languages = excluded.languages,
        countries = excluded.countries,
        genres = excluded.genres,
        plot_summary = excluded.plot_summary,
        tmdb_id = excluded.tmdb_id,
        poster_path = excluded.poster_path,
        metadata_source = 'tmdb',
        metadata_match_status = 'imported',
        metadata_updated_at = now(),
        search_boost_text = excluded.search_boost_text,
        search_embedding = null,
        embedding_model = null
    returning id, movie_key, wikipedia_movie_id;
"""

update_existing_movie_sql = """
    update movies
    set tmdb_id = %(tmdb_id)s,
        poster_path = %(poster_path)s,
        metadata_source = 'tmdb',
        metadata_match_status = 'matched',
        metadata_updated_at = now(),
        search_boost_text = %(search_boost_text)s,
        search_embedding = null,
        embedding_model = null
    where id = %(movie_id)s
    returning id, movie_key, wikipedia_movie_id;
"""

upsert_external_id_sql = """
    insert into movie_external_ids (
        movie_id,
        source,
        external_id,
        metadata,
        updated_at
    )
    values (
        %(movie_id)s,
        %(source)s,
        %(external_id)s,
        %(metadata)s,
        now()
    )
    on conflict (source, external_id)
    do update set
        movie_id = excluded.movie_id,
        metadata = excluded.metadata,
        updated_at = now();
"""

upsert_search_document_sql = """
    insert into movie_search_documents (
        movie_id,
        movie_key,
        wikipedia_movie_id,
        title,
        document_type,
        source,
        source_document_id,
        content,
        metadata,
        updated_at
    )
    values (
        %(movie_id)s,
        %(movie_key)s,
        %(wikipedia_movie_id)s,
        %(title)s,
        %(document_type)s,
        %(source)s,
        %(source_document_id)s,
        %(content)s,
        %(metadata)s,
        now()
    )
    on conflict (source, document_type, source_document_id)
    do update set
        movie_id = excluded.movie_id,
        movie_key = excluded.movie_key,
        wikipedia_movie_id = excluded.wikipedia_movie_id,
        title = excluded.title,
        content = excluded.content,
        metadata = excluded.metadata,
        updated_at = now()
    returning id;
"""

database_size_sql = """
    select pg_database_size(current_database());
"""


def movie_payload_to_db_record(
    movie_payload: dict[str, Any],
) -> dict[str, object]:
    tmdb_id = int(movie_payload["id"])
    title = normalize_text(movie_payload.get("title"))

    if not title:
        title = normalize_text(movie_payload.get("original_title"))

    overview = normalize_text(movie_payload.get("overview"))
    genres = extract_genres(movie_payload)

    return {
        "movie_key": f"tmdb:{tmdb_id}",
        "title": title,
        "release_date": normalize_text(movie_payload.get("release_date")) or None,
        "runtime": movie_payload.get("runtime"),
        "languages": Jsonb(movie_payload.get("spoken_languages") or []),
        "countries": Jsonb(movie_payload.get("production_countries") or []),
        "genres": Jsonb(genres),
        "plot_summary": overview,
        "tmdb_id": tmdb_id,
        "poster_path": movie_payload.get("poster_path"),
        "search_boost_text": build_search_boost_text(movie_payload),
    }


def movie_identity_from_row(row) -> dict[str, object]:
    if row is None or len(row) != 3:
        raise ValueError(f"expected movie identity row with 3 columns, got {row!r}")

    return {
        "movie_id": int(row[0]),
        "movie_key": str(row[1]),
        "wikipedia_movie_id": (
            str(row[2])
            if row[2] is not None
            else None
        ),
    }


def find_existing_movie(
    cursor,
    tmdb_id: int,
) -> dict[str, object] | None:
    cursor.execute(
        find_movie_by_tmdb_external_id_sql,
        {
            "external_id": str(tmdb_id),
        },
    )
    row = cursor.fetchone()

    if row is not None:
        return movie_identity_from_row(row)

    cursor.execute(
        find_movie_by_tmdb_id_sql,
        {
            "tmdb_id": tmdb_id,
        },
    )
    row = cursor.fetchone()

    if row is not None:
        return movie_identity_from_row(row)

    return None


def has_import_storage_capacity(
    cursor,
    tmdb_id: int,
    maximum_database_size_mb: int,
) -> bool:
    if find_existing_movie(cursor, tmdb_id) is not None:
        return True

    cursor.execute(database_size_sql)
    row = cursor.fetchone()

    if row is None or len(row) != 1:
        raise ValueError(f"expected database size row, got {row!r}")

    maximum_size_bytes = maximum_database_size_mb * 1024 * 1024
    return int(row[0]) < maximum_size_bytes


def upsert_movie(
    cursor,
    movie_payload: dict[str, Any],
    include_missing_overview: bool,
    minimum_overview_length: int = default_minimum_overview_length,
) -> int | None:
    record = movie_payload_to_db_record(movie_payload)

    if not record["title"]:
        print(f"skipped missing title: {record['tmdb_id']}")
        return None

    overview_length = len(str(record["plot_summary"]))

    if (
        overview_length < minimum_overview_length
        and not include_missing_overview
    ):
        print(
            "skipped weak overview: "
            f"{record['tmdb_id']} {record['title']} "
            f"({overview_length} chars)"
        )
        return None

    tmdb_id = int(record["tmdb_id"])
    existing_movie = find_existing_movie(cursor, tmdb_id)

    if existing_movie is None:
        cursor.execute(insert_tmdb_movie_sql, record)
        movie_identity = movie_identity_from_row(cursor.fetchone())
        print(f"inserted tmdb movie: {tmdb_id} {record['title']}")
    else:
        update_record = {
            **record,
            "movie_id": existing_movie["movie_id"],
        }
        cursor.execute(update_existing_movie_sql, update_record)
        movie_identity = movie_identity_from_row(cursor.fetchone())
        print(f"updated existing movie: {tmdb_id} {record['title']}")

    movie_id = int(movie_identity["movie_id"])

    cursor.execute(
        upsert_external_id_sql,
        {
            "movie_id": movie_id,
            "source": "tmdb",
            "external_id": str(tmdb_id),
            "metadata": Jsonb(
                {
                    "title": record["title"],
                    "release_date": record["release_date"],
                }
            ),
        },
    )

    return movie_id



def collect_tmdb_ids(
    client,
    args: argparse.Namespace,
) -> list[int]:
    if args.tmdb_ids:
        return list(dict.fromkeys(args.tmdb_ids))

    if args.source == "discover":
        return fetch_discover_movie_ids(
            client=client,
            limit=args.limit,
            page_start=args.page_start,
            page_end=args.page_end,
            discover_mode=args.discover_mode,
            minimum_vote_count=args.minimum_vote_count,
            release_date_from=args.release_date_from,
            release_date_to=args.release_date_to,
        )

    if args.source == "changes":
        return fetch_changed_movie_ids(
            client=client,
            limit=args.limit,
            start_date=args.start_date,
            end_date=args.end_date,
        )

    return []


def main() -> None:
    args = parse_args()

    if args.limit < 1:
        raise ValueError("limit must be at least one")

    if args.delay_ms < 0:
        raise ValueError("delay-ms must be zero or greater")

    if args.page_start < 1:
        raise ValueError("page-start must be at least one")

    if args.page_end is not None and args.page_end < args.page_start:
        raise ValueError("page-end must be greater than or equal to page-start")

    if args.minimum_vote_count < 0:
        raise ValueError("minimum-vote-count must be zero or greater")

    if args.minimum_overview_length < 0:
        raise ValueError("minimum-overview-length must be zero or greater")

    if args.max_database_size_mb < 1:
        raise ValueError("max-database-size-mb must be at least one")

    statistics = {
        "seen": 0,
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "storage_blocked": 0,
    }

    with create_tmdb_client() as client:
        tmdb_ids = collect_tmdb_ids(
            client=client,
            args=args,
        )

        if args.limit:
            tmdb_ids = tmdb_ids[: args.limit]

        if not tmdb_ids:
            print("no TMDB ids to import")
            return

        with get_connection() as connection:
            with connection.cursor() as cursor:
                for tmdb_id in tmdb_ids:
                    statistics["seen"] += 1

                    try:
                        movie_payload = fetch_movie_details(
                            client=client,
                            tmdb_id=tmdb_id,
                        )
                        if not has_import_storage_capacity(
                            cursor=cursor,
                            tmdb_id=tmdb_id,
                            maximum_database_size_mb=(
                                args.max_database_size_mb
                            ),
                        ):
                            statistics["storage_blocked"] += 1
                            print(
                                "stopped import at database storage budget: "
                                f"{args.max_database_size_mb} MB"
                            )
                            break

                        movie_id = upsert_movie(
                            cursor=cursor,
                            movie_payload=movie_payload,
                            include_missing_overview=(
                                args.include_missing_overview
                            ),
                            minimum_overview_length=(
                                args.minimum_overview_length
                            ),
                        )

                        if movie_id is None:
                            statistics["skipped"] += 1
                        else:
                            statistics["imported"] += 1

                        connection.commit()
                    except Exception as error:
                        connection.rollback()
                        statistics["failed"] += 1
                        print(f"failed tmdb movie {tmdb_id}: {error}")

                    time.sleep(args.delay_ms / 1000)

    print()
    print("TMDB import complete")

    for name, value in statistics.items():
        print(f"{name}: {value}")




if __name__ == "__main__":
    main()
