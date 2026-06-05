from backend.app.services.search import search_movies
from backend.app.services.vector_search import search_movies_by_embedding

rrf_k = 60
candidate_multiplier = 5
minimum_candidate_limit = 20
maximum_candidate_limit = 50
minimum_vector_score = 0.35

def get_candidate_limit(limit: int) -> int:
    candidate_limit = limit * candidate_multiplier
    candidate_limit = max(candidate_limit, minimum_candidate_limit)
    return min(candidate_limit, maximum_candidate_limit)


def add_ranked_results(
        combined: dict[str, dict[str, object]], 
        results: list[dict[str, object]], 
        minimum_score: float | None = None, 
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
        
        combined[movie_id]["score"] = float(combined[movie_id]["score"]) + (1 / (rrf_k + rank))

def search_movies_hybrid(query: str, limit: int = 5) -> list[dict[str, object]]:
    candidate_limit = get_candidate_limit(limit)

    full_text_results = search_movies(query, candidate_limit)
    vector_results = search_movies_by_embedding(query, candidate_limit)

    combined: dict[str, dict[str, object]] = {}

    add_ranked_results(combined, full_text_results)
    add_ranked_results(combined, vector_results, minimum_score=minimum_vector_score)

    ranked_results = sorted(
        combined.values(), 
        key = lambda  movie: (-float(movie["score"]), str(movie["title"])),
    )

    return ranked_results[:limit]

