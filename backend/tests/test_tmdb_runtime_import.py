from backend.app.services import tmdb_runtime_import


def build_movie(title: str) -> dict[str, object]:
    return {
        "movie_key": "cmu:1",
        "wikipedia_movie_id": "1",
        "title": title,
        "release_date": None,
        "genres": [],
        "plot_summary": "",
        "score": 1.0,
    }


def test_runtime_fallback_skips_when_local_exact_title_exists(
    monkeypatch,
):
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_read_access_token",
        "token",
    )

    assert not tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="The Matrix",
        local_results=[build_movie("The Matrix")],
    )


def test_runtime_fallback_allows_missing_title_like_query(
    monkeypatch,
):
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_read_access_token",
        "token",
    )

    assert tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="Toy Story 5",
        local_results=[build_movie("Toy Story")],
    )


def test_runtime_fallback_skips_non_marker_query_with_local_results(
    monkeypatch,
):
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_read_access_token",
        "token",
    )

    assert not tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="red pill blue pill",
        local_results=[build_movie("The Matrix")],
    )


def test_runtime_fallback_allows_empty_local_results(
    monkeypatch,
):
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_read_access_token",
        "token",
    )

    assert tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="Oppenheimer",
        local_results=[],
    )


def test_runtime_fallback_skips_when_tmdb_token_missing(
    monkeypatch,
):
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_read_access_token",
        None,
    )

    assert not tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="Toy Story 5",
        local_results=[],
    )


def test_import_tmdb_title_returns_false_when_tmdb_has_no_exact_match(
    monkeypatch,
):
    monkeypatch.setattr(
        tmdb_runtime_import,
        "should_try_tmdb_title_fallback",
        lambda query, local_results: True,
    )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

    monkeypatch.setattr(
        tmdb_runtime_import,
        "create_tmdb_client",
        lambda: FakeClient(),
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "search_tmdb_movie",
        lambda client, title, release_date: None,
    )

    assert not tmdb_runtime_import.import_tmdb_title_if_needed(
        query="red pill blue pill",
        local_results=[],
    )
