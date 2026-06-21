import os

import pytest

from backend.app.services.broad_search import (
    search_movies_broad_full_text,
)


requires_database = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="set RUN_DB_TESTS=1 to run database tests",
)


@requires_database
def test_broad_search_recovers_hockey_mask_movie():
    results = search_movies_broad_full_text(
        "hockey mask summer camp",
        limit=50,
    )

    result_ids = {
        str(movie["wikipedia_movie_id"])
        for movie in results
    }

    assert "13053911" in result_ids


@requires_database
def test_broad_search_keeps_nonsense_queries_empty():
    queries = [
        "zzzxxy",
        "purple toaster moon detective",
        "zzqvplm cinema memory",
        "banana spaceship courtroom",
        "invisible penguin tax office",
    ]

    for query in queries:
        assert search_movies_broad_full_text(
            query,
            limit=50,
        ) == []