from backend.app.services.movie_results import (
    movie_result_from_row,
)


def test_movie_result_builds_poster_url():
    row = (
        "123",
        "Test Movie",
        "2000-01-01",
        ["Drama"],
        "Movie plot",
        456,
        "/poster.jpg",
        "tmdb",
        0.5,
    )

    result = movie_result_from_row(row)

    assert result["wikipedia_movie_id"] == "123"
    assert result["tmdb_id"] == 456
    assert result["poster_url"] == (
        "https://image.tmdb.org/t/p/"
        "w342/poster.jpg"
    )
    assert result["score"] == 0.5


def test_movie_result_handles_missing_poster():
    row = (
        "123",
        "Test Movie",
        None,
        [],
        "Movie plot",
        None,
        None,
        None,
        0.5,
    )

    result = movie_result_from_row(row)

    assert result["poster_path"] is None
    assert result["poster_url"] is None