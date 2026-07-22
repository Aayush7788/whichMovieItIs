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
    requested_params = []

    def fake_request_tmdb_json(client, path, params):
        requested_params.append(params)
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

    assert [params["page"] for params in requested_params] == [2, 3]
    assert all(
        params["sort_by"] == "popularity.desc"
        for params in requested_params
    )
    assert all(
        params["vote_count.gte"] == 25
        for params in requested_params
    )
    assert movie_ids == [21, 22, 31]


def test_fetch_recent_movie_ids_uses_release_filters(monkeypatch):
    captured_params = {}

    def fake_request_tmdb_json(client, path, params):
        captured_params.update(params)
        return {
            "results": [{"id": 101}],
            "total_pages": 1,
        }

    monkeypatch.setattr(
        import_tmdb_movies,
        "request_tmdb_json",
        fake_request_tmdb_json,
    )

    movie_ids = import_tmdb_movies.fetch_discover_movie_ids(
        client=object(),
        limit=1,
        discover_mode="recent",
        minimum_vote_count=50,
        release_date_from="2026-01-01",
        release_date_to="2026-07-09",
    )

    assert movie_ids == [101]
    assert captured_params["sort_by"] == "primary_release_date.desc"
    assert captured_params["vote_count.gte"] == 50
    assert captured_params["primary_release_date.gte"] == "2026-01-01"
    assert captured_params["primary_release_date.lte"] == "2026-07-09"


def test_import_storage_guard_blocks_new_movie_at_limit(monkeypatch):
    class FakeCursor:
        def execute(self, sql):
            self.sql = sql

        def fetchone(self):
            return (450 * 1024 * 1024,)

    monkeypatch.setattr(
        import_tmdb_movies,
        "find_existing_movie",
        lambda cursor, tmdb_id: None,
    )

    assert not import_tmdb_movies.has_import_storage_capacity(
        cursor=FakeCursor(),
        tmdb_id=123,
        maximum_database_size_mb=450,
    )


def test_import_storage_guard_allows_existing_movie(monkeypatch):
    monkeypatch.setattr(
        import_tmdb_movies,
        "find_existing_movie",
        lambda cursor, tmdb_id: {
            "movie_id": 1,
            "movie_key": "tmdb:123",
            "wikipedia_movie_id": None,
        },
    )

    assert import_tmdb_movies.has_import_storage_capacity(
        cursor=object(),
        tmdb_id=123,
        maximum_database_size_mb=450,
    )