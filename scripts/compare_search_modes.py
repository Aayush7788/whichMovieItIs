from backend.app.services.search import search_movies
from backend.app.services.vector_search import search_movies_by_embedding
from scripts.evaluate_search import load_cases
from backend.app.services.hybrid_search import search_movies_hybrid

limit = 5

search_modes = [
    ("full-text", search_movies), 
    ("vector", search_movies_by_embedding), 
    ("hybrid", search_movies_hybrid),
]

def format_titles(results):
    return " | ".join(
        f"{movie['title']} ({float(movie['score']):.4f})" 
        for movie in results
    ) or "<no results>"

def hit_status(case, results):
    expected_titles = set(case["expected_any"])
    must_find = case.get("must_find", bool(expected_titles))
    titles = [movie["title"] for movie in results]

    if must_find:
        return "pass" if any(title in expected_titles for title in titles) else "fail"
    
    return "pass" if len(titles) == 0 else "fail"

def main():
    cases = load_cases()

    for case in cases:
        query = case["query"]

        expected = ", ".join(case["expected_any"]) or "<no results>"

        print(f"query: {query}")
        print(f"expected: {expected}")

        for mode_name, search_function in search_modes:
            results = search_function(query, limit)
            status = hit_status(case, results)
            print(f"{mode_name} [{status}]: {format_titles(results)}")

        print()

if __name__ == "__main__":
    main()
