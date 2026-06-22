from backend.app.services.tmdb import (
    build_poster_url,
)


def movie_result_from_row(
    row: tuple[object, ...],
) -> dict[str, object]:
    poster_path = (
        str(row[6])
        if row[6] is not None
        else None
    )

    return {
        "wikipedia_movie_id": str(row[0]),
        "title": str(row[1]),
        "release_date": row[2],
        "genres": list(row[3] or []),
        "plot_summary": str(row[4]),
        "tmdb_id": (
            int(row[5])
            if row[5] is not None
            else None
        ),
        "poster_path": poster_path,
        "poster_url": build_poster_url(
            poster_path
        ),
        "metadata_source": (
            str(row[7])
            if row[7] is not None
            else None
        ),
        "score": (
            float(row[8])
            if row[8] is not None
            else None
        ),
    }