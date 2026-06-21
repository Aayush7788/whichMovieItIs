# search evaluation

input file:
- `data/evaluation/search_qrels.jsonl`

Current result file:
- `evals/search-evaluation.json`

the qrels file stores known relevant movies by `movie_id`, `title`, and graded relevance.
grades are
- `3`: best match
- `2`: acceptable match
- `1`: weak or related match

## Metrics
- `hit@5`: whether a relevant movie appears in the top 5
- `mrr@10`: how early the first relevant movie appears in the top 10
- `recall@10`: how many known relevant movies appear in the top 10
- `ndcg@10`: ranking quality using graded relevance
- `no_result_correct`: whether nonsense queries correctly return no results   
- `avg_latency_ms`: average query latency
- `p95_latency_ms`: high-end latency for slower cases

## results
   Mode         full-text
   hit@5        0.6923
   mrr@10       0.5192
   recall@10    0.6806
   ndcg@10      0.5455
   no_result    1.0000
   avg latency  ~36ms
   p95 latency  ~59ms
  ───────────────────────────────────────────────────────────────────────────────────
   Mode         vector
   hit@5        0.4615
   mrr@10       0.3333
   recall@10    0.4444
   ndcg@10      0.3480
   no_result    0.0000
   avg latency  ~594ms
   p95 latency  ~5585ms
  ───────────────────────────────────────────────────────────────────────────────────
   Mode         hybrid
   hit@5        0.8462
   mrr@10       0.6769
   recall@10    0.8472
   ndcg@10      0.6806
   no_result    1.0000
   avg latency  ~99ms
   p95 latency  ~114ms
  ───────────────────────────────────────────────────────────────────────────────────
   Mode         reranked
   hit@5        0.8462
   mrr@10       0.5872
   recall@10    0.7639
   ndcg@10      0.6000
   no_result    1.0000
   avg latency  ~1252ms
   p95 latency  ~4715ms

## findings
hybrid is the current best mode.

full-text is fast and handles no-result queries correctly, but it misses semantic memory queries like time travel car and toys come alive.

vector search alone is not ready. It helps some semantic cases, but it returns results for input like zzzxxy.

so, hybrid gives the best quality/speed balance.

## default
hybrid search is now product default.

## hybrid
added a cached parameter sweep:

- `scripts/tune_hybrid_search.py`
- `evals/hybrid-tuning-results.json`

the sweep evaluates ranking configurations without repeating expensive database and embedding retri.

## Handling edge cases
- hybrid and reranked search returned unrelated results for three of five no result queries
- false positive: 
   full text find nothing 
   but vector retrival return weak similarities with confidence

Rules:

- individual vector candidates still require score `0.40`
- when full-text returns no candidates, the top vector score must be at least `0.50`
- otherwise the search returns no results
