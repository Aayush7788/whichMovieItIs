from backend.app.db import get_connection
from backend.app.services.movie_results import (
    movie_result_from_row,
)

memory_clue_search_sql = """
    with search_query as (
        select websearch_to_tsquery('english', %(query)s) as query
    ),
    clue_matches as (
        select
            clue.movie_id,
            max(
                ts_rank_cd(
                    clue.search_vector,
                    search_query.query
                )
            )::double precision as score
        from movie_memory_clues clue
        cross join search_query
        where clue.search_vector @@ search_query.query
        group by clue.movie_id
        order by score desc
        limit %(limit)s
    )
    select
        movie.movie_key,
        movie.wikipedia_movie_id,
        movie.title,
        movie.release_date,
        movie.genres,
        movie.plot_summary,
        movie.tmdb_id,
        movie.poster_path,
        movie.metadata_source,
        clue_matches.score
    from clue_matches
    join movies movie
        on movie.id = clue_matches.movie_id
    order by
        clue_matches.score desc,
        movie.title
    limit %(limit)s;
"""


def search_movies_by_memory_clues(
    query: str,
    limit: int = 5,
) -> list[dict[str, object]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                memory_clue_search_sql,
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