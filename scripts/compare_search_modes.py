from backend.app.services.search import search_movies
from backend.app.services.vector_search import search_movies_by_embedding
from scripts.evaluate_search import (
    binary_relevance_grade, 
    load_cases, 
    relevance_by_movie_id, 
    result_movie_id,
)   
from backend.app.services.hybrid_search import search_movies_hybrid
from backend.app.services.reranker import search_movies_reranked

limit = 5

search_modes = [
    ("full-text", search_movies), 
    ("vector", search_movies_by_embedding), 
    ("hybrid", search_movies_hybrid),
    ("reranked", search_movies_reranked),
]

def format_expected(case):
    relevant_movies = case["relevant"]
    if not relevant_movies:
        return "<no result expected>"
    
    return " | ".join(
        (
            f"{movie['title']} "
            f"#{movie['movie_id']} "
            f"grade={movie['grade']}"
        )
        for movie in relevant_movies
    )

def format_results(results, relevance):
    if not results:
        return "<no results>"

    formatted_results = []

    for movie in results:
        movie_id = result_movie_id(movie)
        grade = relevance.get(movie_id, 0)

        raw_score = movie.get("score")
        score = float(raw_score) if raw_score is not None else 0.0

        formatted_results.append(
            (
                f"{movie['title']} "
                f"#{movie_id} "
                f"grade={grade} "
                f"score={score:.4f}"
            )
        )

    return " | ".join(formatted_results)


def hit_status(relevance, results):
    acceptable_movie_ids = {
        movie_id
        for movie_id, grade in relevance.items()
        if grade >= binary_relevance_grade
    }

    if not acceptable_movie_ids:
        return "pass" if len(results) == 0 else "fail"

    found_relevant_movie = any(
        result_movie_id(movie) in acceptable_movie_ids
        for movie in results
    )

    return "pass" if found_relevant_movie else "fail"

def main():
    cases = load_cases()

    for case in cases:
        query = case["query"]
        relevance = relevance_by_movie_id(case)

        print(f"query: {query}")
        print(f"expected: {format_expected(case)}")

        for mode_name, search_function in search_modes:
            results = search_function(query, limit)
            status = hit_status(relevance, results)
            formatted_result = format_results(results, relevance)
            print(f"{mode_name} [{status}]: {formatted_result}")


        print()

if __name__ == "__main__":
    main()
