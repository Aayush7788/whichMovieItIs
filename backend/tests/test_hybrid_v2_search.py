from backend.app.services import hybrid_v2_search


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
        "tmdb_id": None,
        "poster_path": None,
        "poster_url": None,
        "metadata_source": None,
        "score": score,
    }


def test_hybrid_v2_uses_document_full_text_candidates(
    monkeypatch,
):
    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movies",
        lambda query, limit: [],
    )
    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movies_by_embedding",
        lambda query, limit: [],
    )
    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movies_broad_full_text",
        lambda query, limit: [],
    )
    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movie_documents_by_embedding",
        lambda query, limit: [],
    )

    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movie_documents_full_text",
        lambda query, limit: [
            build_movie(
                "13053911",
                "Friday the 13th",
                0.8,
            )
        ],
    )

    results = hybrid_v2_search.search_movies_hybrid_v2(
        "hockey mask summer camp",
        limit=5,
    )

    assert results[0]["wikipedia_movie_id"] == "13053911"


def test_hybrid_v2_suppresses_weak_vector_only_results(
    monkeypatch,
):
    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movies",
        lambda query, limit: [],
    )
    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movies_broad_full_text",
        lambda query, limit: [],
    )
    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movie_documents_full_text",
        lambda query, limit: [],
    )
    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movies_by_embedding",
        lambda query, limit: [
            build_movie("1", "Weak Movie Vector", 0.2),
        ],
    )
    monkeypatch.setattr(
        hybrid_v2_search,
        "search_movie_documents_by_embedding",
        lambda query, limit: [
            build_movie("2", "Weak Document Vector", 0.3),
        ],
    )

    assert (
        hybrid_v2_search.search_movies_hybrid_v2(
            "zzzxxy",
            limit=5,
        )
        == []
    )


def test_rank_hybrid_v2_deduplicates_shared_movie():
    shared_movie = build_movie(
        "1",
        "Shared Movie",
        1.0,
    )

    results = hybrid_v2_search.rank_hybrid_v2_results(
        full_text_results=[shared_movie],
        vector_results=[],
        broad_results=[],
        document_full_text_results=[shared_movie],
        document_vector_results=[],
        limit=5,
    )

    assert len(results) == 1
    assert results[0]["wikipedia_movie_id"] == "1"