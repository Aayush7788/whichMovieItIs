import logging
from time import perf_counter

from backend.app.services.search import search_movies
from backend.app.services.vector_search import search_movies_by_embedding
from backend.app.services.broad_search import search_movies_broad_full_text
from backend.app.services.clue_search import search_movies_by_memory_clues
from backend.app.services.tmdb_runtime_import import import_tmdb_title_if_needed

logger = logging.getLogger(__name__)

rrf_k = 60
candidate_multiplier = 5
minimum_candidate_limit = 20
maximum_candidate_limit = 50
minimum_vector_score = 0.40
minimum_vector_only_score = 0.50
full_text_weight = 1.5
vector_weight = 1.25
broad_weight = 4.0
clue_weight = 6.0
score_confidence_weight = 0.5

def get_candidate_limit(limit: int) -> int:
    candidate_limit = limit * candidate_multiplier
    candidate_limit = max(candidate_limit, minimum_candidate_limit)
    return min(candidate_limit, maximum_candidate_limit)

def should_return_no_results(
    full_text_results: list[dict[str, object]],
    vector_results: list[dict[str, object]],
    broad_results: list[dict[str, object]] | None = None,
    minimum_vector_only_score_value: float = minimum_vector_only_score,
) -> bool:
    if full_text_results or broad_results:
        return False

    if not vector_results:
        return True

    top_vector_score = vector_results[0].get("score")

    if top_vector_score is None:
        return True

    return (
        float(top_vector_score)
        < minimum_vector_only_score_value
    )

def add_ranked_results(
        combined: dict[str, dict[str, object]], 
        results: list[dict[str, object]], 
    minimum_score: float | None = None,
    weight: float = 1.0,
    rrf_k_value: int = rrf_k,
    score_confidence_weight_value: float = 0.0,
) -> None:
    eligible_results = []

    for rank, movie in enumerate(results, start=1):
        raw_score = float(movie.get("score") or 0.0)

        if minimum_score is not None:
            if raw_score < minimum_score:
                continue

        eligible_results.append((rank, movie, max(raw_score, 0.0)))

    maximum_raw_score = max(
        (
            raw_score
            for _, _, raw_score in eligible_results
        ),
        default=0.0,
    )

    for rank, movie, raw_score in eligible_results:
        movie_id = str(
            movie.get("movie_key")
            or movie.get("wikipedia_movie_id")
        )

        if movie_id not in combined:
            combined[movie_id] = dict(movie)
            combined[movie_id]["score"] = 0.0

        normalized_score = (
            raw_score / maximum_raw_score
            if maximum_raw_score > 0
            else 0.0
        )
        confidence_multiplier = (
            1.0
            + score_confidence_weight_value
            * normalized_score
        )
        rank_score = (
            weight
            / (rrf_k_value + rank)
            * confidence_multiplier
        )

        combined[movie_id]["score"] = (
            float(combined[movie_id]["score"])
            + rank_score
        )

def rank_hybrid_results(
    full_text_results: list[dict[str, object]],
    vector_results: list[dict[str, object]],
    limit: int,
    broad_results: list[dict[str, object]] | None = None,
    clue_results: list[dict[str, object]] | None = None,
    rrf_k_value: int = rrf_k,
    minimum_vector_score_value: float = minimum_vector_score,
    full_text_weight_value: float = full_text_weight,
    vector_weight_value: float = vector_weight,
    broad_weight_value: float = broad_weight,
    clue_weight_value: float = clue_weight,
    score_confidence_weight_value: float = score_confidence_weight,
) -> list[dict[str, object]]:
    combined: dict[str, dict[str, object]] = {}

    add_ranked_results(
        combined=combined,
        results=full_text_results,
        weight=full_text_weight_value,
        rrf_k_value=rrf_k_value,
        score_confidence_weight_value=score_confidence_weight_value,
    )

    add_ranked_results(
        combined=combined,
        results=vector_results,
        minimum_score=minimum_vector_score_value,
        weight=vector_weight_value,
        rrf_k_value=rrf_k_value,
        score_confidence_weight_value=score_confidence_weight_value,
    )
    if broad_results:
        add_ranked_results(
            combined=combined,
            results=broad_results,
            weight=broad_weight_value,
            rrf_k_value=rrf_k_value,
            score_confidence_weight_value=score_confidence_weight_value,
        )
    if clue_results:
        add_ranked_results(
        combined=combined,
        results=clue_results,
        weight=clue_weight_value,
        rrf_k_value=rrf_k_value,
        score_confidence_weight_value=score_confidence_weight_value,
    )

    ranked_results = sorted(
        combined.values(),
        key=lambda movie: (
            -float(movie["score"]),
            str(movie["title"]),
        ),
    )

    return ranked_results[:limit]


def search_movies_hybrid_local(query: str, limit: int = 5) -> list[dict[str, object]]:
    candidate_limit = get_candidate_limit(limit)

    full_text_results = search_movies(query, candidate_limit)
    vector_results = search_movies_by_embedding(query, candidate_limit)
    broad_results = search_movies_broad_full_text(query, candidate_limit)
    clue_results = search_movies_by_memory_clues(
        query,
        candidate_limit,
    )

    lexical_results = [
        *full_text_results,
        *clue_results,
    ]

    if should_return_no_results(
        full_text_results=lexical_results,
        vector_results=vector_results,
        broad_results=broad_results
    ):
        return []

    return rank_hybrid_results(
        full_text_results=full_text_results,
        vector_results=vector_results,
        broad_results=broad_results,
        limit=limit,
        clue_results=clue_results,
    )


def search_movies_hybrid(query: str, limit: int = 5) -> list[dict[str, object]]:
    started_at = perf_counter()
    results = search_movies_hybrid_local(query, limit)
    fallback_imported = False

    if import_tmdb_title_if_needed(
        query=query,
        local_results=results,
    ):
        fallback_imported = True
        results = search_movies_hybrid_local(query, limit)

    latency_ms = (perf_counter() - started_at) * 1000
    logger.info(
        (
            "search completed query=%r limit=%s "
            "results=%s fallback_imported=%s latency_ms=%.1f"
        ),
        query,
        limit,
        len(results),
        fallback_imported,
        latency_ms,
    )

    return results

