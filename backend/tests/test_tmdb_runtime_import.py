from time import perf_counter, sleep

from backend.app.services import tmdb_runtime_import


def clear_runtime_fallback_state() -> None:
    with tmdb_runtime_import.runtime_fallback_lock:
        tmdb_runtime_import.runtime_fallback_request_times.clear()
        tmdb_runtime_import.runtime_fallback_query_attempts.clear()


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
    clear_runtime_fallback_state()
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
    clear_runtime_fallback_state()
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
    clear_runtime_fallback_state()
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_read_access_token",
        "token",
    )

    assert not tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="red pill blue pill",
        local_results=[build_movie("The Matrix")],
    )
    assert not tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="lightsaber",
        local_results=[build_movie("Star Wars")],
    )


def test_runtime_fallback_allows_article_title_with_weak_local_results(
    monkeypatch,
):
    clear_runtime_fallback_state()
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_read_access_token",
        "token",
    )

    assert tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="The Life of Chuck",
        local_results=[build_movie("Cast Away")],
    )


def test_runtime_fallback_allows_empty_local_results(
    monkeypatch,
):
    clear_runtime_fallback_state()
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_read_access_token",
        "token",
    )

    assert tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="Oppenheimer",
        local_results=[],
    )


def test_runtime_fallback_skips_plot_like_empty_results(
    monkeypatch,
):
    clear_runtime_fallback_state()
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_read_access_token",
        "token",
    )

    assert not tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="invisible penguin tax office",
        local_results=[],
    )
    assert not tmdb_runtime_import.should_try_tmdb_title_fallback(
        query="zzzxxy",
        local_results=[],
    )


def test_runtime_fallback_skips_when_tmdb_token_missing(
    monkeypatch,
):
    clear_runtime_fallback_state()
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
    clear_runtime_fallback_state()
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
        lambda timeout_seconds=None: FakeClient(),
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "search_tmdb_movie",
        lambda client, title, release_date, maximum_attempts: None,
    )

    result = tmdb_runtime_import.import_tmdb_title_if_needed(
        query="red pill blue pill",
        local_results=[],
    )

    assert result == tmdb_runtime_import.RuntimeTmdbFallbackResult()


def test_runtime_fallback_rate_limits_requests(monkeypatch):
    clear_runtime_fallback_state()
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_runtime_fallback_max_requests_per_window",
        1,
    )
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_runtime_fallback_rate_limit_window_seconds",
        60,
    )
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_runtime_fallback_query_cache_seconds",
        1800,
    )

    assert tmdb_runtime_import.acquire_runtime_fallback_slot("Shrek 5")
    assert not tmdb_runtime_import.acquire_runtime_fallback_slot("Scream 7")


def test_runtime_fallback_uses_strict_timeout_and_schedules_documents(
    monkeypatch,
):
    clear_runtime_fallback_state()
    captured = {
        "timeouts": [],
    }

    monkeypatch.setattr(
        tmdb_runtime_import,
        "should_try_tmdb_title_fallback",
        lambda query, local_results: True,
    )
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_runtime_fallback_timeout_seconds",
        2.5,
    )
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_runtime_fallback_max_attempts",
        1,
    )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def cursor(self):
            return FakeCursor()

        def commit(self):
            captured["committed"] = True

    def fake_create_tmdb_client(timeout_seconds=None):
        captured["timeouts"].append(timeout_seconds)
        return FakeClient()

    def fake_search_tmdb_movie(client, title, release_date, maximum_attempts):
        captured["search_attempts"] = maximum_attempts
        return {"id": 421892}

    def fake_fetch_movie_details(client, tmdb_id, maximum_attempts):
        captured["detail_attempts"] = maximum_attempts
        return {"id": tmdb_id}

    monkeypatch.setattr(
        tmdb_runtime_import,
        "create_tmdb_client",
        fake_create_tmdb_client,
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "search_tmdb_movie",
        fake_search_tmdb_movie,
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "fetch_movie_details",
        fake_fetch_movie_details,
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "get_connection",
        lambda: FakeConnection(),
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "assess_runtime_persistence",
        lambda cursor, tmdb_id: (
            tmdb_runtime_import.RuntimePersistenceDecision(
                allowed=True,
                database_size_bytes=100 * 1024 * 1024,
            )
        ),
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "upsert_tmdb_movie",
        lambda cursor, movie_payload: 123,
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "schedule_document_embedding_backfill",
        lambda movie_id: captured.update({"scheduled_movie_id": movie_id}),
    )

    result = tmdb_runtime_import.import_tmdb_title_if_needed(
        query="Shrek 5",
        local_results=[],
    )

    assert result.imported
    assert result.transient_movie is None
    assert len(captured["timeouts"]) == 2
    assert all(
        0 < timeout <= 2.5
        for timeout in captured["timeouts"]
    )
    assert captured["search_attempts"] == 1
    assert captured["detail_attempts"] == 1
    assert captured["committed"] is True
    assert captured["scheduled_movie_id"] == 123


def test_runtime_fallback_skips_when_timeout_disabled(monkeypatch):
    clear_runtime_fallback_state()
    monkeypatch.setattr(
        tmdb_runtime_import,
        "should_try_tmdb_title_fallback",
        lambda query, local_results: True,
    )
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_runtime_fallback_timeout_seconds",
        0,
    )

    result = tmdb_runtime_import.import_tmdb_title_if_needed(
        query="Shrek 5",
        local_results=[],
    )

    assert result == tmdb_runtime_import.RuntimeTmdbFallbackResult()


def test_runtime_fallback_enforces_hard_deadline(monkeypatch):
    clear_runtime_fallback_state()
    monkeypatch.setattr(
        tmdb_runtime_import,
        "should_try_tmdb_title_fallback",
        lambda query, local_results: True,
    )
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_runtime_fallback_timeout_seconds",
        0.05,
    )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

    monkeypatch.setattr(
        tmdb_runtime_import,
        "create_tmdb_client",
        lambda timeout_seconds=None: FakeClient(),
    )

    def slow_search(*args, **kwargs):
        sleep(0.2)
        return None

    monkeypatch.setattr(
        tmdb_runtime_import,
        "search_tmdb_movie",
        slow_search,
    )

    started_at = perf_counter()
    result = tmdb_runtime_import.import_tmdb_title_if_needed(
        query="Shrek 5",
        local_results=[],
    )
    elapsed_seconds = perf_counter() - started_at

    assert result == tmdb_runtime_import.RuntimeTmdbFallbackResult()
    assert elapsed_seconds < 0.15

def test_runtime_fallback_returns_transient_movie_over_storage_budget(
    monkeypatch,
):
    clear_runtime_fallback_state()
    captured = {}

    monkeypatch.setattr(
        tmdb_runtime_import,
        "should_try_tmdb_title_fallback",
        lambda query, local_results: True,
    )
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_runtime_fallback_timeout_seconds",
        2.5,
    )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def cursor(self):
            return FakeCursor()

        def commit(self):
            captured["committed"] = True

    monkeypatch.setattr(
        tmdb_runtime_import,
        "create_tmdb_client",
        lambda timeout_seconds=None: FakeClient(),
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "search_tmdb_movie",
        lambda client, title, release_date, maximum_attempts: {
            "id": 123456,
        },
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "fetch_movie_details",
        lambda client, tmdb_id, maximum_attempts: {
            "id": tmdb_id,
            "title": "Storage Budget Movie",
            "release_date": "2026-07-01",
            "overview": "A movie returned without database persistence.",
            "genres": [{"name": "Drama"}],
            "poster_path": "/poster.jpg",
        },
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "get_connection",
        lambda: FakeConnection(),
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "assess_runtime_persistence",
        lambda cursor, tmdb_id: (
            tmdb_runtime_import.RuntimePersistenceDecision(
                allowed=False,
                database_size_bytes=460 * 1024 * 1024,
            )
        ),
    )
    monkeypatch.setattr(
        tmdb_runtime_import,
        "upsert_tmdb_movie",
        lambda cursor, movie_payload: (_ for _ in ()).throw(
            AssertionError("over-budget movie must not be persisted")
        ),
    )

    result = tmdb_runtime_import.import_tmdb_title_if_needed(
        query="Storage Budget Movie",
        local_results=[],
    )

    assert not result.imported
    assert result.transient_movie is not None
    assert result.transient_movie["movie_key"] == "tmdb:123456"
    assert result.transient_movie["title"] == "Storage Budget Movie"
    assert "committed" not in captured

def test_runtime_persistence_denies_new_movie_at_storage_limit(
    monkeypatch,
):
    class FakeCursor:
        def execute(self, sql):
            self.sql = sql

        def fetchone(self):
            return (450 * 1024 * 1024,)

    monkeypatch.setattr(
        tmdb_runtime_import,
        "find_existing_movie",
        lambda cursor, tmdb_id: None,
    )
    monkeypatch.setattr(
        tmdb_runtime_import.settings,
        "tmdb_runtime_persistence_max_database_mb",
        450,
    )

    decision = tmdb_runtime_import.assess_runtime_persistence(
        cursor=FakeCursor(),
        tmdb_id=123456,
    )

    assert not decision.allowed
    assert decision.database_size_bytes == 450 * 1024 * 1024
