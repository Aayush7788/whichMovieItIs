from backend.app.db import get_connection
from backend.app.services.movie_results import (
    movie_result_from_row,
)
search_movie_sql = """
    with search_query as (
        select websearch_to_tsquery('english', %(query)s) as query
    )
    select
        m.movie_key,
        m.wikipedia_movie_id,
        m.title,
        m.release_date,
        m.genres,
        m.plot_summary,
        m.tmdb_id,
        m.poster_path,
        m.metadata_source,
        ts_rank_cd(m.search_vector, search_query.query)::double precision as score
        from movies m
        cross join search_query
        where m.search_vector @@ search_query.query
        order by
            score desc,
            m.title
        limit %(limit)s;
    """

def search_movies(query: str, limit: int = 5) -> list[dict[str, object]]:

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                search_movie_sql, 
                {
                    "query": query, 
                    "limit": limit,
                },
            )
            rows = cur.fetchall()
    # results = []

    # for row in rows:
    #     results.append(
    #         {
    #             "wikipedia_movie_id": row[0], 
    #             "title": row[1], 
    #             "release_date": row[2],
    #             "genres": row[3],
    #             "plot_summary": row[4],
    #             "score": float(row[5]) if row[5] is not None else None,
    #         }
    #     )
    # return results
    return [
        movie_result_from_row(row)
        for row in rows
    ]

