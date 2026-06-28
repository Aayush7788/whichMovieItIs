from backend.app.services.broad_search import (
    search_movies_broad_full_text,
)
from backend.app.services.document_search import (
    search_movie_documents_by_embedding,
    search_movie_documents_full_text,
)
from backend.app.services.hybrid_search import (
    add_ranked_results,
    broad_weight,
    full_text_weight,
    get_candidate_limit,
    minimum_vector_score,
    minimum_vector_only_score,
    rrf_k,
    should_return_no_results,
    vector_weight,
)
from backend.app.services.search import search_movies
from backend.app.services.vector_search import (
    search_movies_by_embedding,
)


document_full_text_weight = 1.5
document_vector_weight = 0.8
minimum_document_vector_score = 0.40


def _sort_vector_results_for_guard(
    movie_vector_results: list[dict[str, object]],
    document_vector_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    vector_results = [
        *movie_vector_results,
        *document_vector_results,
    ]

    return sorted(
        vector_results,
        key=lambda movie: float(movie.get("score") or 0.0),
        reverse=True,
    )


def rank_hybrid_v2_results(
    full_text_results: list[dict[str, object]],
    vector_results: list[dict[str, object]],
    broad_results: list[dict[str, object]],
    document_full_text_results: list[dict[str, object]],
    document_vector_results: list[dict[str, object]],
    limit: int,
    rrf_k_value: int = rrf_k,
) -> list[dict[str, object]]:
    combined: dict[str, dict[str, object]] = {}

    add_ranked_results(
        combined=combined,
        results=full_text_results,
        weight=full_text_weight,
        rrf_k_value=rrf_k_value,
    )
    add_ranked_results(
        combined=combined,
        results=vector_results,
        minimum_score=minimum_vector_score,
        weight=vector_weight,
        rrf_k_value=rrf_k_value,
    )
    add_ranked_results(
        combined=combined,
        results=broad_results,
        weight=broad_weight,
        rrf_k_value=rrf_k_value,
    )
    add_ranked_results(
        combined=combined,
        results=document_full_text_results,
        weight=document_full_text_weight,
        rrf_k_value=rrf_k_value,
    )
    add_ranked_results(
        combined=combined,
        results=document_vector_results,
        minimum_score=minimum_document_vector_score,
        weight=document_vector_weight,
        rrf_k_value=rrf_k_value,
    )

    ranked_results = sorted(
        combined.values(),
        key=lambda movie: (
            -float(movie["score"]),
            str(movie["title"]),
        ),
    )

    return ranked_results[:limit]


def search_movies_hybrid_v2(
    query: str,
    limit: int = 5,
) -> list[dict[str, object]]:
    candidate_limit = get_candidate_limit(limit)

    full_text_results = search_movies(
        query,
        candidate_limit,
    )
    vector_results = search_movies_by_embedding(
        query,
        candidate_limit,
    )
    broad_results = search_movies_broad_full_text(
        query,
        candidate_limit,
    )
    document_full_text_results = search_movie_documents_full_text(
        query=query,
        limit=candidate_limit,
    )
    document_vector_results = search_movie_documents_by_embedding(
        query=query,
        limit=candidate_limit,
    )

    lexical_results = [
        *full_text_results,
        *document_full_text_results,
    ]
    vector_guard_results = _sort_vector_results_for_guard(
        movie_vector_results=vector_results,
        document_vector_results=document_vector_results,
    )

    if should_return_no_results(
        full_text_results=lexical_results,
        vector_results=vector_guard_results,
        broad_results=broad_results,
        minimum_vector_only_score_value=minimum_vector_only_score,
    ):
        return []

    return rank_hybrid_v2_results(
        full_text_results=full_text_results,
        vector_results=vector_results,
        broad_results=broad_results,
        document_full_text_results=document_full_text_results,
        document_vector_results=document_vector_results,
        limit=limit,
    )