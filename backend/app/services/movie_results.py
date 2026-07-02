from backend.app.services.tmdb import (
    build_poster_url,
)


def movie_result_from_row(
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
    "score": (
        float(row[9])
        if row[9] is not None
        else None
    ),
}