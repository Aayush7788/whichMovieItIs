from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from queue import Queue
from threading import Lock, Thread
from time import monotonic
from typing import Any, Callable, TypeVar

import httpx
from psycopg.types.json import Jsonb

from backend.app.config import settings
from backend.app.db import get_connection
from backend.app.services.embeddings import (
    build_movie_embedding_text,
    embed_text,
    embedding_model_name,
    normalize_text as normalize_embedding_text,
    to_pgvector_literal,
)
from backend.app.services.tmdb import (
    build_poster_url,
    create_tmdb_client,
    normalize_title,
    request_tmdb_json,
    search_tmdb_movie,
)


logger = logging.getLogger(__name__)

default_language = "en-US"
maximum_runtime_title_words = 8
maximum_runtime_title_chars = 80
tmdb_source = "tmdb"
minimum_runtime_budget_seconds = 0.25
runtime_title_marker_words = {
    "chapter",
    "episode",
    "part",
    "volume",
}
runtime_title_article_words = {
    "a",
    "an",
    "the",
}
runtime_title_number_words = {
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
}
runtime_fallback_lock = Lock()
runtime_fallback_request_times: list[float] = []
runtime_fallback_query_attempts: dict[str, float] = {}
runtime_fallback_result_type = TypeVar("runtime_fallback_result_type")


class RuntimeFallbackDeadlineExceeded(TimeoutError):
    pass


@dataclass(frozen=True)
class RuntimeTmdbFallbackResult:
    imported: bool = False
    transient_movie: dict[str, object] | None = None


@dataclass(frozen=True)
class RuntimePersistenceDecision:
    allowed: bool
    database_size_bytes: int

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
    order by id
    limit 1;
"""


database_size_sql = """
    select pg_database_size(current_database());
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
        'runtime_imported',
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
        metadata_match_status = 'runtime_imported',
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
        metadata_match_status = 'runtime_matched',
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
        'tmdb',
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
        'tmdb',
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
    returning id, document_type, content;
"""


update_movie_embedding_sql = """
    update movies
    set search_embedding = %(embedding)s::vector,
        embedding_model = %(model)s
    where id = %(movie_id)s;
"""


upsert_document_embedding_sql = """
    insert into movie_search_document_embeddings (
        document_id,
        embedding,
        embedding_model,
        updated_at
    )
    values (
        %(document_id)s,
        %(embedding)s::vector,
        %(model)s,
        now()
    )
    on conflict (document_id)
    do update set
        embedding = excluded.embedding,
        embedding_model = excluded.embedding_model,
        updated_at = now();
"""


select_movie_embedding_text_sql = """
    select title, plot_summary, search_boost_text
    from movies
    where id = %(movie_id)s;
"""


select_unembedded_movie_documents_sql = """
    select
        document.id,
        document.title,
        document.document_type,
        document.content
    from movie_search_documents document
    left join movie_search_document_embeddings embedding
        on embedding.document_id = document.id
    where document.movie_id = %(movie_id)s
        and (
            embedding.document_id is null
            or embedding.embedding_model is distinct from %(model)s
        )
    order by document.id;
"""


def clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def list_text(values: Iterable[object]) -> str:
    cleaned_values = [
        clean_text(value)
        for value in values
        if clean_text(value)
    ]
    return ", ".join(cleaned_values)


def extract_genres(movie_payload: dict[str, Any]) -> list[str]:
    raw_genres = movie_payload.get("genres")

    if not isinstance(raw_genres, list):
        return []

    return [
        clean_text(genre.get("name"))
        for genre in raw_genres
        if isinstance(genre, dict) and clean_text(genre.get("name"))
    ]


def extract_keywords(movie_payload: dict[str, Any]) -> list[str]:
    keywords_payload = movie_payload.get("keywords")

    if not isinstance(keywords_payload, dict):
        return []

    raw_keywords = keywords_payload.get("keywords")

    if not isinstance(raw_keywords, list):
        return []

    return [
        clean_text(keyword.get("name"))
        for keyword in raw_keywords
        if isinstance(keyword, dict) and clean_text(keyword.get("name"))
    ]


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

        name = clean_text(cast_member.get("name"))
        character = clean_text(cast_member.get("character"))

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

        job = clean_text(crew_member.get("job"))

        if job not in useful_jobs:
            continue

        name = clean_text(crew_member.get("name"))

        if name:
            crew_names.append(f"{job}: {name}")

        if len(crew_names) >= limit:
            break

    return crew_names


def build_search_boost_text(movie_payload: dict[str, Any]) -> str:
    title = clean_text(movie_payload.get("title"))
    original_title = clean_text(movie_payload.get("original_title"))
    tagline = clean_text(movie_payload.get("tagline"))
    overview = clean_text(movie_payload.get("overview"))
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

    return clean_text(" ".join(section for section in sections if section))


def build_tmdb_documents(
    movie_payload: dict[str, Any],
) -> list[dict[str, object]]:
    tmdb_id = int(movie_payload["id"])
    title = clean_text(movie_payload.get("title"))
    overview = clean_text(movie_payload.get("overview"))
    tagline = clean_text(movie_payload.get("tagline"))
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


def build_movie_record(
    movie_payload: dict[str, Any],
) -> dict[str, object]:
    tmdb_id = int(movie_payload["id"])
    title = clean_text(movie_payload.get("title"))

    if not title:
        title = clean_text(movie_payload.get("original_title"))

    return {
        "movie_key": f"tmdb:{tmdb_id}",
        "title": title,
        "release_date": clean_text(movie_payload.get("release_date")) or None,
        "runtime": movie_payload.get("runtime"),
        "languages": Jsonb(movie_payload.get("spoken_languages") or []),
        "countries": Jsonb(movie_payload.get("production_countries") or []),
        "genres": Jsonb(extract_genres(movie_payload)),
        "plot_summary": clean_text(movie_payload.get("overview")),
        "tmdb_id": tmdb_id,
        "poster_path": movie_payload.get("poster_path"),
        "search_boost_text": build_search_boost_text(movie_payload),
    }


def build_transient_movie_result(
    movie_payload: dict[str, Any],
) -> dict[str, object]:
    record = build_movie_record(movie_payload)
    poster_path = (
        str(record["poster_path"])
        if record["poster_path"] is not None
        else None
    )

    return {
        "movie_key": str(record["movie_key"]),
        "wikipedia_movie_id": None,
        "title": str(record["title"]),
        "release_date": record["release_date"],
        "genres": extract_genres(movie_payload),
        "plot_summary": str(record["plot_summary"]),
        "tmdb_id": int(record["tmdb_id"]),
        "poster_path": poster_path,
        "poster_url": build_poster_url(poster_path),
        "metadata_source": tmdb_source,
        "score": 1.0,
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


def local_results_include_exact_title(
    query: str,
    local_results: list[dict[str, object]],
) -> bool:
    expected_title = normalize_title(query)

    return any(
        normalize_title(str(movie.get("title") or "")) == expected_title
        for movie in local_results
    )


def query_looks_like_runtime_title(query: str) -> bool:
    normalized_query = normalize_title(query)

    if not normalized_query:
        return False

    words = normalized_query.split()

    return (
        1 <= len(words) <= maximum_runtime_title_words
        and len(normalized_query) <= maximum_runtime_title_chars
    )


def query_has_runtime_title_marker(query: str) -> bool:
    if any(character.isdigit() for character in query):
        return True

    if ":" in query:
        return True

    words = set(normalize_title(query).split())

    return bool(
        words & runtime_title_marker_words
        and words & runtime_title_number_words
    )


def query_has_strong_runtime_title_shape(query: str) -> bool:
    if query_has_runtime_title_marker(query):
        return True

    words = normalize_title(query).split()

    return bool(
        2 <= len(words) <= 5
        and words[0] in runtime_title_article_words
    )


def query_has_runtime_title_shape(query: str) -> bool:
    if query_has_strong_runtime_title_shape(query):
        return True

    words = normalize_title(query).split()

    return bool(
        len(words) == 1
        and any(
            vowel in words[0]
            for vowel in "aeiou"
        )
    )


def prune_runtime_fallback_state(now: float) -> None:
    request_window_seconds = (
        settings.tmdb_runtime_fallback_rate_limit_window_seconds
    )
    query_cache_seconds = (
        settings.tmdb_runtime_fallback_query_cache_seconds
    )

    runtime_fallback_request_times[:] = [
        request_time
        for request_time in runtime_fallback_request_times
        if now - request_time < request_window_seconds
    ]

    expired_queries = [
        query
        for query, request_time in runtime_fallback_query_attempts.items()
        if now - request_time >= query_cache_seconds
    ]

    for query in expired_queries:
        runtime_fallback_query_attempts.pop(query, None)


def acquire_runtime_fallback_slot(query: str) -> bool:
    query_key = normalize_title(query)
    now = monotonic()

    with runtime_fallback_lock:
        prune_runtime_fallback_state(now)

        if query_key in runtime_fallback_query_attempts:
            return False

        if (
            len(runtime_fallback_request_times)
            >= settings.tmdb_runtime_fallback_max_requests_per_window
        ):
            return False

        runtime_fallback_query_attempts[query_key] = now
        runtime_fallback_request_times.append(now)

    return True


def remaining_runtime_budget_seconds(deadline: float) -> float:
    return max(deadline - monotonic(), 0.0)


def has_runtime_budget(
    deadline: float,
    minimum_seconds: float = minimum_runtime_budget_seconds,
) -> bool:
    return remaining_runtime_budget_seconds(deadline) > minimum_seconds


def should_try_tmdb_title_fallback(
    query: str,
    local_results: list[dict[str, object]],
) -> bool:
    if not settings.tmdb_read_access_token:
        return False

    if not query_looks_like_runtime_title(query):
        return False

    if local_results_include_exact_title(
        query=query,
        local_results=local_results,
    ):
        return False

    if local_results and not query_has_strong_runtime_title_shape(query):
        return False

    if not local_results and not query_has_runtime_title_shape(query):
        return False

    return True


def run_with_runtime_deadline(
    callback: Callable[[], runtime_fallback_result_type],
    deadline: float,
) -> runtime_fallback_result_type:
    result_queue: Queue[
        tuple[bool, runtime_fallback_result_type | BaseException]
    ] = Queue(maxsize=1)

    def run_callback() -> None:
        try:
            result_queue.put((True, callback()))
        except BaseException as error:
            result_queue.put((False, error))

    thread = Thread(
        target=run_callback,
        daemon=True,
    )
    thread.start()
    thread.join(remaining_runtime_budget_seconds(deadline))

    if thread.is_alive():
        raise RuntimeFallbackDeadlineExceeded(
            "TMDB runtime fallback exceeded its deadline"
        )

    succeeded, result = result_queue.get_nowait()

    if not succeeded:
        raise result

    return result


def fetch_movie_details(
    client: httpx.Client,
    tmdb_id: int,
    maximum_attempts: int = 4,
) -> dict[str, Any]:
    payload = request_tmdb_json(
        client=client,
        path=f"/movie/{tmdb_id}",
        params={
            "append_to_response": "keywords,credits",
            "language": default_language,
        },
        maximum_attempts=maximum_attempts,
    )

    payload["id"] = tmdb_id
    return payload


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


def assess_runtime_persistence(
    cursor,
    tmdb_id: int,
) -> RuntimePersistenceDecision:
    if find_existing_movie(cursor, tmdb_id) is not None:
        return RuntimePersistenceDecision(
            allowed=True,
            database_size_bytes=0,
        )

    cursor.execute(database_size_sql)
    row = cursor.fetchone()

    if row is None or len(row) != 1:
        raise ValueError(
            f"expected database size row with 1 column, got {row!r}"
        )

    database_size_bytes = int(row[0])
    maximum_size_bytes = (
        settings.tmdb_runtime_persistence_max_database_mb
        * 1024
        * 1024
    )

    return RuntimePersistenceDecision(
        allowed=database_size_bytes < maximum_size_bytes,
        database_size_bytes=database_size_bytes,
    )


def build_document_embedding_text(
    title: str,
    document_type: str,
    content: str,
) -> str:
    text = f"{title}. {document_type}. {content}"
    return normalize_embedding_text(text)[:4000]


def update_movie_embedding(
    cursor,
    movie_id: int,
) -> None:
    cursor.execute(
        select_movie_embedding_text_sql,
        {
            "movie_id": movie_id,
        },
    )
    row = cursor.fetchone()

    if row is None:
        raise ValueError(f"movie not found for embedding: {movie_id}")

    text = build_movie_embedding_text(
        title=str(row[0] or ""),
        plot_summary=str(row[1] or ""),
        search_boost_text=str(row[2] or ""),
    )

    cursor.execute(
        update_movie_embedding_sql,
        {
            "movie_id": movie_id,
            "embedding": to_pgvector_literal(embed_text(text)),
            "model": embedding_model_name,
        },
    )


def upsert_document_embedding(
    cursor,
    document_id: int,
    title: str,
    document_type: str,
    content: str,
) -> None:
    text = build_document_embedding_text(
        title=title,
        document_type=document_type,
        content=content,
    )

    cursor.execute(
        upsert_document_embedding_sql,
        {
            "document_id": document_id,
            "embedding": to_pgvector_literal(embed_text(text)),
            "model": embedding_model_name,
        },
    )


def backfill_document_embeddings_for_movie(movie_id: int) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                select_unembedded_movie_documents_sql,
                {
                    "movie_id": movie_id,
                    "model": embedding_model_name,
                },
            )
            rows = cursor.fetchall()

            for row in rows:
                upsert_document_embedding(
                    cursor=cursor,
                    document_id=int(row[0]),
                    title=str(row[1] or ""),
                    document_type=str(row[2] or ""),
                    content=str(row[3] or ""),
                )

            connection.commit()


def schedule_document_embedding_backfill(movie_id: int) -> None:
    thread = Thread(
        target=backfill_document_embeddings_for_movie,
        args=(movie_id,),
        daemon=True,
    )
    thread.start()


def upsert_tmdb_movie(
    cursor,
    movie_payload: dict[str, Any],
) -> int | None:
    record = build_movie_record(movie_payload)

    if not record["title"]:
        return None

    tmdb_id = int(record["tmdb_id"])
    existing_movie = find_existing_movie(cursor, tmdb_id)

    if existing_movie is None:
        cursor.execute(insert_tmdb_movie_sql, record)
        movie_identity = movie_identity_from_row(cursor.fetchone())
    else:
        update_record = {
            **record,
            "movie_id": existing_movie["movie_id"],
        }
        cursor.execute(update_existing_movie_sql, update_record)
        movie_identity = movie_identity_from_row(cursor.fetchone())

    movie_id = int(movie_identity["movie_id"])

    cursor.execute(
        upsert_external_id_sql,
        {
            "movie_id": movie_id,
            "external_id": str(tmdb_id),
            "metadata": Jsonb(
                {
                    "title": record["title"],
                    "release_date": record["release_date"],
                }
            ),
        },
    )

    update_movie_embedding(cursor, movie_id)

    return movie_id



def import_tmdb_title_if_needed(
    query: str,
    local_results: list[dict[str, object]],
) -> RuntimeTmdbFallbackResult:
    empty_result = RuntimeTmdbFallbackResult()

    if not should_try_tmdb_title_fallback(
        query=query,
        local_results=local_results,
    ):
        logger.info(
            (
                "tmdb runtime fallback skipped query=%r "
                "reason=not_title_fallback_candidate local_results=%s"
            ),
            query,
            len(local_results),
        )
        return empty_result

    if not acquire_runtime_fallback_slot(query):
        logger.info(
            (
                "tmdb runtime fallback skipped query=%r "
                "reason=rate_limited_or_cached"
            ),
            query,
        )
        return empty_result

    try:
        fallback_started_at = monotonic()
        timeout_budget_seconds = (
            settings.tmdb_runtime_fallback_timeout_seconds
        )

        if timeout_budget_seconds <= 0:
            logger.info(
                (
                    "tmdb runtime fallback skipped query=%r "
                    "reason=timeout_disabled"
                ),
                query,
            )
            return empty_result

        deadline = fallback_started_at + timeout_budget_seconds
        maximum_attempts = max(
            settings.tmdb_runtime_fallback_max_attempts,
            1,
        )

        def search_for_match():
            with create_tmdb_client(
                timeout_seconds=(
                    remaining_runtime_budget_seconds(deadline)
                ),
            ) as client:
                return search_tmdb_movie(
                    client=client,
                    title=query,
                    release_date=None,
                    maximum_attempts=maximum_attempts,
                )

        match = run_with_runtime_deadline(
            search_for_match,
            deadline,
        )

        if match is None:
            logger.info(
                (
                    "tmdb runtime fallback completed query=%r "
                    "result=no_exact_match"
                ),
                query,
            )
            return empty_result

        if not has_runtime_budget(deadline):
            logger.info(
                (
                    "tmdb runtime fallback skipped query=%r "
                    "reason=deadline_exhausted stage=details"
                ),
                query,
            )
            return empty_result

        def fetch_details():
            with create_tmdb_client(
                timeout_seconds=(
                    remaining_runtime_budget_seconds(deadline)
                ),
            ) as client:
                return fetch_movie_details(
                    client=client,
                    tmdb_id=int(match["id"]),
                    maximum_attempts=maximum_attempts,
                )

        movie_payload = run_with_runtime_deadline(
            fetch_details,
            deadline,
        )

        if not has_runtime_budget(deadline):
            logger.info(
                (
                    "tmdb runtime fallback skipped query=%r "
                    "reason=deadline_exhausted stage=db_import"
                ),
                query,
            )
            return empty_result

        with get_connection() as connection:
            with connection.cursor() as cursor:
                persistence = assess_runtime_persistence(
                    cursor=cursor,
                    tmdb_id=int(movie_payload["id"]),
                )

                if not persistence.allowed:
                    logger.warning(
                        (
                            "tmdb runtime fallback persistence skipped "
                            "query=%r reason=database_storage_budget "
                            "database_size_mb=%.1f limit_mb=%s"
                        ),
                        query,
                        persistence.database_size_bytes / 1024 / 1024,
                        settings.tmdb_runtime_persistence_max_database_mb,
                    )
                    return RuntimeTmdbFallbackResult(
                        transient_movie=build_transient_movie_result(
                            movie_payload
                        ),
                    )

                movie_id = upsert_tmdb_movie(
                    cursor=cursor,
                    movie_payload=movie_payload,
                )
                connection.commit()

        if movie_id is not None:
            logger.info(
                (
                    "tmdb runtime fallback imported query=%r "
                    "tmdb_id=%s movie_id=%s latency_ms=%.1f"
                ),
                query,
                movie_payload.get("id"),
                movie_id,
                (monotonic() - fallback_started_at) * 1000,
            )

        return RuntimeTmdbFallbackResult(
            imported=movie_id is not None,
        )
    except (
        httpx.HTTPError,
        RuntimeError,
        RuntimeFallbackDeadlineExceeded,
        ValueError,
    ) as error:
        logger.warning(
            "tmdb runtime fallback failed query=%r error=%s",
            query,
            error,
        )
        return empty_result
