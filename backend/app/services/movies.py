from backend.app.db import get_connection
from backend.app.services.tmdb import build_poster_url


movie_catalog_sql = """
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
        source
    from movies
    order by
        (poster_path is null),
        case
            when release_date ~ '^\d{4}-\d{2}-\d{2}$'
                and release_date::date > current_date
            then 1
            else 0
        end,
        release_date desc nulls last,
        title
    limit %(limit)s
    offset %(offset)s;
"""

movie_count_sql = """
    select count(*)::integer
    from movies;
"""

movie_detail_sql = """
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
        source,
        freebase_movie_id,
        box_office_revenue,
        runtime,
        languages,
        countries,
        search_boost_text
    from movies
    where movie_key = %(movie_key)s;
"""


def movie_catalog_item_from_row(
    row: tuple[object, ...],
) -> dict[str, object]:
    poster_path = (
        str(row[7])
        if row[7] is not None
        else None
    )

    return {
        "movie_key": str(row[0]),
        "wikipedia_movie_id": (
            str(row[1])
            if row[1] is not None
            else None
        ),
        "title": str(row[2]),
        "release_date": row[3],
        "genres": list(row[4] or []),
        "plot_summary": str(row[5]),
        "tmdb_id": (
            int(row[6])
            if row[6] is not None
            else None
        ),
        "poster_path": poster_path,
        "poster_url": build_poster_url(poster_path),
        "metadata_source": (
            str(row[8])
            if row[8] is not None
            else None
        ),
        "source": str(row[9]),
    }


def movie_detail_from_row(
    row: tuple[object, ...],
) -> dict[str, object]:
    movie = movie_catalog_item_from_row(row[:10])
    movie.update(
        {
            "freebase_movie_id": (
                str(row[10])
                if row[10] is not None
                else None
            ),
            "box_office_revenue": (
                float(row[11])
                if row[11] is not None
                else None
            ),
            "runtime": (
                float(row[12])
                if row[12] is not None
                else None
            ),
            "languages": list(row[13] or []),
            "countries": list(row[14] or []),
            "search_boost_text": (
                str(row[15])
                if row[15]
                else None
            ),
        },
    )
    return movie


def list_movies(
    limit: int = 24,
    offset: int = 0,
) -> dict[str, object]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(movie_count_sql)
            total = int(cur.fetchone()[0])

            cur.execute(
                movie_catalog_sql,
                {
                    "limit": limit,
                    "offset": offset,
                },
            )
            rows = cur.fetchall()

    return {
        "results": [
            movie_catalog_item_from_row(row)
            for row in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_movie_detail(
    movie_key: str,
) -> dict[str, object] | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                movie_detail_sql,
                {
                    "movie_key": movie_key,
                },
            )
            row = cur.fetchone()

    if row is None:
        return None

    return movie_detail_from_row(row)
