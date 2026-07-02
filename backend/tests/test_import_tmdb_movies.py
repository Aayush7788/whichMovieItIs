import pytest

from scripts import import_tmdb_movies


def test_movie_identity_from_row_accepts_full_identity_row():
    result = import_tmdb_movies.movie_identity_from_row(
        (123, "cmu:456", "456")
    )

    assert result == {
        "movie_id": 123,
        "movie_key": "cmu:456",
        "wikipedia_movie_id": "456",
    }


def test_movie_identity_from_row_rejects_partial_identity_row():
    with pytest.raises(ValueError, match="expected movie identity row"):
        import_tmdb_movies.movie_identity_from_row((123,))


def test_fetch_discover_movie_ids_uses_requested_pages(monkeypatch):
    requested_pages = []

    def fake_request_tmdb_json(client, path, params):
        requested_pages.append(params["page"])
        return {
            "results": [
                {"id": params["page"] * 10 + 1},
                {"id": params["page"] * 10 + 2},
            ],
            "total_pages": 10,
        }

    monkeypatch.setattr(
        import_tmdb_movies,
        "request_tmdb_json",
        fake_request_tmdb_json,
    )

    movie_ids = import_tmdb_movies.fetch_discover_movie_ids(
        client=object(),
        limit=3,
        page_start=2,
        page_end=3,
    )

    assert requested_pages == [2, 3]
    assert movie_ids == [21, 22, 31]
