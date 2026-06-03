from backend.app.services.search import search_movies
from backend.app.services.vector_search import search_movies_by_embedding
from scripts.evaluate_search import load_cases

limit = 5

def format_titles(results):
    return " | ".join(movie["title"] for movie in results) or "<no result>" 

def main():
    cases = load_cases()

    for case in cases:
        query = case["query"]

        full_text_result = search_movies(query, limit)
        vector_results = search_movies_by_embedding(query, limit)

        print(f"query: {query}")
        print(f"full-text: {format_titles(full_text_result)}")
        print(f"vector: {format_titles(vector_results)}")

        print()

if __name__ == "__main__":
    main()
