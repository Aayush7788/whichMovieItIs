from backend.app.db import get_connection
from backend.app.services.embeddings import embed_text, to_pgvector_literal
from backend.app.services.movie_results import (
    movie_result_from_row,
)

def search_movies_by_embedding(query: str, limit: int = 5) -> list[dict[str, object]]:
    query_embedding = to_pgvector_literal(embed_text(query))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                vector_search_sql, 
                {
                    "embedding": query_embedding,
                    "limit": limit,
                },
            )
            rows = cur.fetchall()
    results = []
    for row in rows:
        results.append(
            {
                "wikipedia_movie_id": row[0],
                "title": row[1],
                "release_date": row[2],
                "genres": row[3],
                "plot_summary": row[4],
                "score": float(row[5]) if row[5] is not None else None,
            }
        )
    # return results
    return [
        movie_result_from_row(row)
        for row in rows
    ]

vector_search_sql = """
    select
        movie_key,
        wikipedia_movie_id,
        title,
        release_date,
        genres,
        plot_summary,
        tmdb_id,
        poster_path,
        metadata_source,
        1 - (search_embedding <=> %(embedding)s::vector) as score
    from movies
    where search_embedding is not null
    order by search_embedding <=> %(embedding)s::vector, title
    limit %(limit)s;
"""