import argparse
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
from backend.app.services.broad_search import (
    search_movies_broad_full_text,
)
from backend.app.services.document_search import search_movies_document_hybrid
from backend.app.services.hybrid_v2_search import search_movies_hybrid_v2

default_limit = 5

search_modes = [
    ("full-text", search_movies), 
    ("broad-full-text", search_movies_broad_full_text),
    ("vector", search_movies_by_embedding), 
    ("hybrid", search_movies_hybrid),
    ("reranked", search_movies_reranked),
    ("document-hybrid", search_movies_document_hybrid),
    ("hybrid-v2", search_movies_hybrid_v2),
]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id")
    parser.add_argument(
        "--limit",
        type=int,
        default=default_limit,
    )
    parser.add_argument(
        "--skip-reranked",
        action="store_true",
    )
    return parser.parse_args()

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
    args = parse_args()
    cases = load_cases()

    if args.case_id:
        cases = [
            case
            for case in cases
            if case["id"] == args.case_id
        ]

        if not cases:
            raise ValueError(
                f"qrel case not found: {args.case_id}"
            )

    selected_search_modes = [
        mode
        for mode in search_modes
        if not (
            args.skip_reranked
            and mode[0] == "reranked"
        )
    ]

    for case in cases:
        query = case["query"]
        relevance = relevance_by_movie_id(case)

        print(f"case: {case['id']}")
        print(f"query: {query}")
        print(f"expected: {format_expected(case)}")

        for mode_name, search_function in selected_search_modes:
            results = search_function(
                query,
                args.limit,
            )
            status = hit_status(
                relevance,
                results,
            )
            formatted_result = format_results(
                results,
                relevance,
            )
            print(
                f"{mode_name} [{status}]: "
                f"{formatted_result}"
            )

        print()

if __name__ == "__main__":
    main()
