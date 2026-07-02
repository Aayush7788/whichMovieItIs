from __future__ import annotations

from collections.abc import Iterable
from typing import Any

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
    create_tmdb_client,
    normalize_title,
    request_tmdb_json,
    search_tmdb_movie,
)


default_language = "en-US"
maximum_runtime_title_words = 8
maximum_runtime_title_chars = 80
tmdb_source = "tmdb"
runtime_title_marker_words = {
    "chapter",
    "episode",
    "part",
    "volume",
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

    if local_results and not query_has_runtime_title_marker(query):
        return False

    return True


def fetch_movie_details(
    client: httpx.Client,
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
    movie_key = str(movie_identity["movie_key"])
    wikipedia_movie_id = movie_identity["wikipedia_movie_id"]

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

    for document in build_tmdb_documents(movie_payload):
        cursor.execute(
            upsert_search_document_sql,
            {
                "movie_id": movie_id,
                "movie_key": movie_key,
                "wikipedia_movie_id": wikipedia_movie_id,
                "title": record["title"],
                "document_type": document["document_type"],
                "source_document_id": document["source_document_id"],
                "content": document["content"],
                "metadata": Jsonb(document["metadata"]),
            },
        )
        document_id, document_type, content = cursor.fetchone()
        upsert_document_embedding(
            cursor=cursor,
            document_id=int(document_id),
            title=str(record["title"]),
            document_type=str(document_type),
            content=str(content),
        )

    return movie_id


def import_tmdb_title_if_needed(
    query: str,
    local_results: list[dict[str, object]],
) -> bool:
    if not should_try_tmdb_title_fallback(
        query=query,
        local_results=local_results,
    ):
        return False

    try:
        with create_tmdb_client() as client:
            match = search_tmdb_movie(
                client=client,
                title=query,
                release_date=None,
            )

            if match is None:
                return False

            movie_payload = fetch_movie_details(
                client=client,
                tmdb_id=int(match["id"]),
            )

        with get_connection() as connection:
            with connection.cursor() as cursor:
                movie_id = upsert_tmdb_movie(
                    cursor=cursor,
                    movie_payload=movie_payload,
                )
                connection.commit()

        return movie_id is not None
    except (
        httpx.HTTPError,
        RuntimeError,
        ValueError,
    ):
        return False
