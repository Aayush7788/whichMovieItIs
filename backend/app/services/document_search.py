from backend.app.db import get_connection
from backend.app.services.embeddings import (
    embed_text,
    to_pgvector_literal,
)
from backend.app.services.hybrid_search import (
    rank_hybrid_results,
    should_return_no_results,
)
from backend.app.services.movie_results import movie_result_from_row


document_candidate_multiplier = 10
minimum_document_candidate_limit = 50
maximum_document_candidate_limit = 150


document_full_text_search_sql = """
    with search_query as (
        select websearch_to_tsquery('english', %(query)s) as query
    ),
    document_matches as (
        select
            document.movie_id,
            max(
                ts_rank_cd(
                    document.search_vector,
                    search_query.query
                )
            ) as score
        from movie_search_documents document
        cross join search_query
        where document.search_vector @@ search_query.query
        group by document.movie_id
        order by score desc
        limit %(limit)s
    )
    select
        movie.wikipedia_movie_id,
        movie.title,
        movie.release_date,
        movie.genres,
        movie.plot_summary,
        movie.tmdb_id,
        movie.poster_path,
        movie.metadata_source,
        document_matches.score
    from document_matches
    join movies movie
        on movie.id = document_matches.movie_id
    order by
        document_matches.score desc,
        movie.title
    limit %(limit)s;
"""


document_vector_search_sql = """
    with document_matches as (
        select
            document.movie_id,
            max(
                1 - (
                    embedding.embedding <=> %(embedding)s::vector
                )
            ) as score,
            min(
                embedding.embedding <=> %(embedding)s::vector
            ) as distance
        from movie_search_document_embeddings embedding
        join movie_search_documents document
            on document.id = embedding.document_id
        group by document.movie_id
        order by distance asc
        limit %(limit)s
    )
    select
        movie.wikipedia_movie_id,
        movie.title,
        movie.release_date,
        movie.genres,
        movie.plot_summary,
        movie.tmdb_id,
        movie.poster_path,
        movie.metadata_source,
        document_matches.score
    from document_matches
    join movies movie
        on movie.id = document_matches.movie_id
    order by
        document_matches.score desc,
        movie.title
    limit %(limit)s;
"""


def get_document_candidate_limit(limit: int) -> int:
    candidate_limit = limit * document_candidate_multiplier
    candidate_limit = max(
        candidate_limit,
        minimum_document_candidate_limit,
    )
    return min(candidate_limit, maximum_document_candidate_limit)


def search_movie_documents_full_text(
    query: str,
    limit: int = 5,
) -> list[dict[str, object]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                document_full_text_search_sql,
                {
                    "query": query,
                    "limit": limit,
                },
            )
            rows = cursor.fetchall()

    return [
        movie_result_from_row(row)
        for row in rows
    ]


def search_movie_documents_by_embedding(
    query: str,
    limit: int = 5,
) -> list[dict[str, object]]:
    query_embedding = to_pgvector_literal(
        embed_text(query)
    )

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                document_vector_search_sql,
                {
                    "embedding": query_embedding,
                    "limit": limit,
                },
            )
            rows = cursor.fetchall()

    return [
        movie_result_from_row(row)
        for row in rows
    ]


def search_movies_document_hybrid(
    query: str,
    limit: int = 5,
) -> list[dict[str, object]]:
    candidate_limit = get_document_candidate_limit(limit)

    full_text_results = search_movie_documents_full_text(
        query=query,
        limit=candidate_limit,
    )
    vector_results = search_movie_documents_by_embedding(
        query=query,
        limit=candidate_limit,
    )

    if should_return_no_results(
        full_text_results=full_text_results,
        vector_results=vector_results,
        broad_results=[],
    ):
        return []

    return rank_hybrid_results(
        full_text_results=full_text_results,
        vector_results=vector_results,
        broad_results=[],
        limit=limit,
    )