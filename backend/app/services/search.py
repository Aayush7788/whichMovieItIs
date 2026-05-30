from backend.app.db import get_connection

search_movie_sql = """
    select
        wikipedia_movie_id, 
        title, 
        release_date, 
        genres, 
        plot_summary
    from movies
    where
        title ilike %(pattern)s
        or plot_summary ilike %(pattern)s
    order by
        case
            when title ilike %(pattern)s then 0
            else 1
        end,
        title
    limit %(limit)s;
"""

def search_movies(query: str, limit: int = 5) -> list[dict[str, object]]:
    pattern = f"%{query}%"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                search_movie_sql, 
                {
                    "pattern": pattern, 
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
                "score": None,
            }
        )
    return results

