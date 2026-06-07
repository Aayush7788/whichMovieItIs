from functools import lru_cache

from sentence_transformers import CrossEncoder
from backend.app.services.hybrid_search import search_movies_hybrid

reranker_model_name = "cross-encoder/ms-marco-MiniLM-L6-v2"
rerank_text_max_chars = 1200
minimum_candidate_limit = 20
maximum_candidate_limit = 30
candiate_multiplier = 4

@lru_cache(maxsize=1)
def get_reranker_model():
    return CrossEncoder(reranker_model_name)

def get_reranker_candidate_limit(limit: int) -> int:
    candiate_limit = limit * candiate_multiplier
    candiate_limit = max(candiate_limit, minimum_candidate_limit)
    return min(candiate_limit, maximum_candidate_limit)

def build_rerank_text(movie: dict[str, object]) -> str:
    title = str(movie.get("title") or "")
    plot_summary = str(movie.get("plot_summary") or "")
    text = f"{title}.{plot_summary}"
    return " ".join(text.split())[:rerank_text_max_chars]

def rerank_candidates(
      query: str,
      candidates: list[dict[str, object]],
  ) -> list[dict[str, object]]:
      if not candidates:
          return []

      pairs = [
          (query, build_rerank_text(movie))
          for movie in candidates
      ]

      score_values = get_reranker_model().predict(pairs)

      reranked_movies = []
      for movie, score_value in zip(candidates, score_values):
          reranked_movie = dict(movie)
          reranked_movie["score"] = float(score_value)
          reranked_movies.append(reranked_movie)

      return sorted(
          reranked_movies,
          key=lambda movie: (-float(movie["score"]), str(movie["title"])),
      )

def search_movies_reranked(query: str, limit: int = 5) -> list[dict[str, object]]:
    candidate_limit =get_reranker_candidate_limit(limit)
    candidates = search_movies_hybrid(query, limit=candidate_limit)
    reranked_candidates = rerank_candidates(query, candidates)

    return reranked_candidates[:limit]