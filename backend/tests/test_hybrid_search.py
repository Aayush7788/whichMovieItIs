from backend.app.services import hybrid_search

def build_movie(
    movie_id: str,
    title: str,
    score: float,
) -> dict[str, object]:
    return {
        "wikipedia_movie_id": movie_id,
        "title": title,
        "release_date": None,
        "genres": [],
        "plot_summary": "",
        "score": score,
    }


def test_no_result_guard_suppresses_weak_vector_only_results():
    vector_results = [
        build_movie("1", "Weak vector result", 0.49),
    ]

    assert hybrid_search.should_return_no_results(
        full_text_results=[],
        vector_results=vector_results,
        broad_results=[],
    )


def test_broad_results_prevent_no_result_suppression():
    broad_results = [
        build_movie("1", "Broad lexical result", 0.1),
    ]

    assert not hybrid_search.should_return_no_results(
        full_text_results=[],
        vector_results=[],
        broad_results=broad_results,
    )


def test_rank_hybrid_results_fuses_three_sources():
    full_text_results = [
        build_movie("1", "Shared movie", 1.0),
    ]
    vector_results = [
        build_movie("2", "Vector movie", 0.70),
    ]
    broad_results = [
        build_movie("1", "Shared movie", 1.0),
        build_movie("3", "Broad movie", 1.0),
    ]

    results = hybrid_search.rank_hybrid_results(
        full_text_results=full_text_results,
        vector_results=vector_results,
        broad_results=broad_results,
        limit=3,
    )

    result_ids = [
        movie["wikipedia_movie_id"]
        for movie in results
    ]

    assert result_ids[0] == "1"
    assert set(result_ids) == {"1", "2", "3"}
    assert len(result_ids) == len(set(result_ids))


def test_search_movies_hybrid_queries_broad_source(
    monkeypatch,
):
    broad_calls = []

    monkeypatch.setattr(
        hybrid_search,
        "search_movies",
        lambda query, limit: [],
    )
    monkeypatch.setattr(
        hybrid_search,
        "search_movies_by_embedding",
        lambda query, limit: [],
    )

    def fake_broad_search(query, limit):
        broad_calls.append((query, limit))
        return [
            build_movie(
                "13053911",
                "Friday the 13th",
                0.3,
            ),
        ]

    monkeypatch.setattr(
        hybrid_search,
        "search_movies_broad_full_text",
        fake_broad_search,
    )

    results = hybrid_search.search_movies_hybrid(
        "hockey mask summer camp",
        limit=5,
    )

    assert broad_calls == [
        ("hockey mask summer camp", 25),
    ]
    assert results[0]["wikipedia_movie_id"] == "13053911"