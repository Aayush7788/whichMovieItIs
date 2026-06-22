from backend.app.services.tmdb import (
    build_poster_url,
    choose_tmdb_match,
    extract_release_year,
    normalize_title,
)


def test_normalize_title_removes_punctuation():
    assert normalize_title(
        "Oh! What a Lovely War"
    ) == "oh what a lovely war"


def test_extract_release_year():
    assert extract_release_year(
        "1999-03-31"
    ) == "1999"


def test_choose_tmdb_match_uses_release_year():
    results = [
        {
            "id": 1,
            "title": "Cinderella",
            "original_title": "Cinderella",
            "release_date": "1950-02-15",
            "popularity": 20.0,
        },
        {
            "id": 2,
            "title": "Cinderella",
            "original_title": "Cinderella",
            "release_date": "2015-03-12",
            "popularity": 50.0,
        },
    ]

    match = choose_tmdb_match(
        results=results,
        title="Cinderella",
        release_date="1950-02-15",
    )

    assert match is not None
    assert match["id"] == 1


def test_choose_tmdb_match_rejects_ambiguous_title():
    results = [
        {
            "id": 1,
            "title": "Cinderella",
            "original_title": "Cinderella",
            "release_date": "1950-02-15",
        },
        {
            "id": 2,
            "title": "Cinderella",
            "original_title": "Cinderella",
            "release_date": "2015-03-12",
        },
    ]

    assert choose_tmdb_match(
        results=results,
        title="Cinderella",
        release_date=None,
    ) is None


def test_build_poster_url():
    assert build_poster_url(
        "/poster.jpg"
    ) == (
        "https://image.tmdb.org/t/p/"
        "w342/poster.jpg"
    )


def test_build_poster_url_handles_missing_path():
    assert build_poster_url(None) is None