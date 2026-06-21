from backend.app.services.search import search_movies
from backend.app.services.vector_search import search_movies_by_embedding

rrf_k = 60
candidate_multiplier = 5
minimum_candidate_limit = 20
maximum_candidate_limit = 50
minimum_vector_score = 0.40
minimum_vector_only_score = 0.50
full_text_weight = 2.0
vector_weight = 1.0

def get_candidate_limit(limit: int) -> int:
    candidate_limit = limit * candidate_multiplier
    candidate_limit = max(candidate_limit, minimum_candidate_limit)
    return min(candidate_limit, maximum_candidate_limit)

def should_return_no_results(
    full_text_results: list[dict[str, object]],
    vector_results: list[dict[str, object]],
    minimum_vector_only_score_value: float = minimum_vector_only_score,
) -> bool:
    if full_text_results:
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
) -> None:
    for rank, movie in enumerate(results, start=1):
        raw_score = movie.get("score")
        
        if minimum_score is not None:
            if raw_score is None or float(raw_score) < minimum_score:
                continue

        movie_id = str(movie["wikipedia_movie_id"])

        if movie_id not in combined:
            combined[movie_id] = dict(movie)
            combined[movie_id]["score"] = 0.0
        
        combined[movie_id]["score"] = float(combined[movie_id]["score"]) + (weight / (rrf_k_value + rank))

def rank_hybrid_results(
    full_text_results: list[dict[str, object]],
    vector_results: list[dict[str, object]],
    limit: int,
    rrf_k_value: int = rrf_k,
    minimum_vector_score_value: float = minimum_vector_score,
    full_text_weight_value: float = full_text_weight,
    vector_weight_value: float = vector_weight,
) -> list[dict[str, object]]:
    combined: dict[str, dict[str, object]] = {}

    add_ranked_results(
        combined=combined,
        results=full_text_results,
        weight=full_text_weight_value,
        rrf_k_value=rrf_k_value,
    )

    add_ranked_results(
        combined=combined,
        results=vector_results,
        minimum_score=minimum_vector_score_value,
        weight=vector_weight_value,
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


def search_movies_hybrid(query: str, limit: int = 5) -> list[dict[str, object]]:
    candidate_limit = get_candidate_limit(limit)

    full_text_results = search_movies(query, candidate_limit)
    vector_results = search_movies_by_embedding(query, candidate_limit)

    return rank_hybrid_results(
        full_text_results=full_text_results,
        vector_results=vector_results,
        limit=limit,
    )

