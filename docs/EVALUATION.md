# Search Evaluation

WhichMovieItIs uses a maintained judged-query set to measure search quality before changing the stable hybrid route.

## Evaluation Data

- Queries: `data/evaluation/search_queries.jsonl`
- Graded relevance judgments: `data/evaluation/search_qrels.jsonl`
- Latest generated report: `evals/search-evaluation.json`

Current set: 50 cases.

| Intent | Cases |
|---|---:|
| Semantic plot | 15 |
| Object or scene | 8 |
| Exact title | 8 |
| Dialogue memory | 5 |
| Franchise title | 5 |
| No result | 5 |
| Character memory | 4 |

Ranked cases have one or more known relevant movies. Relevance grades are:

- `3`: best expected match
- `2`: acceptable match
- `1`: weak but related match

## Metrics

| Metric | Meaning |
|---|---|
| Hit@5 | Fraction of ranked queries with at least one relevant movie in the first five results |
| MRR@10 | Mean reciprocal rank of the first relevant result in the top ten |
| Recall@10 | Fraction of all judged relevant movies retrieved in the top ten |
| NDCG@10 | Position-sensitive ranking quality using graded relevance, normalized against the ideal ranking |
| No-result correctness | Fraction of nonsense/no-match cases that correctly return an empty list |
| Average latency | Mean end-to-end evaluation-query latency |
| P95 latency | 95th-percentile latency, exposing slower tail behavior |

## Latest Stable-Hybrid Result

Validated local run:

| Metric | Result |
|---|---:|
| Hit@5 | **1.0000** |
| MRR@10 | **0.9285** |
| Recall@10 | **0.9593** |
| NDCG@10 | **0.8859** |
| No-result correctness | **1.0000** |
| Average latency | **406.0909 ms** |
| P95 latency | **930.2597 ms** |

The stable hybrid route is the product default because it gives the best maintained quality/speed balance. Vector-only retrieval can find paraphrases but produces plausible nearest neighbors for nonsense. Strict full-text is precise but misses paraphrases. Broad lexical retrieval recovers partial clue overlap. Fusion combines those strengths.

## Run the Evaluation

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_search_qrels
.\.venv\Scripts\python.exe -m scripts.evaluate_search --mode hybrid
.\.venv\Scripts\python.exe -m scripts.analyze_candidate_recall
```

The evaluator prints the summary and updates generated JSON reports under `evals/`.

## Run Automated Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q

cd frontend
npm.cmd run lint
npm.cmd run build
```

The backend suite covers API validation, database result formatting, hybrid fusion, no-result behavior, TMDB ingestion, runtime fallback, configuration, and catalog endpoints.

## How to Interpret the Numbers

- Hit@5 of 1.0 means every ranked query in this set has a relevant movie somewhere in the first five.
- MRR below 1.0 means the best relevant movie is not always ranked first.
- Recall below 1.0 means some queries have additional judged-relevant alternatives missing from the top ten.
- NDCG is stricter than Hit@5 because it rewards the best movies appearing earlier and in the correct graded order.
- Perfect no-result correctness on five cases is useful but is not enough evidence to claim universal false-positive prevention.

## Limitations

- Fifty queries are too few for universal accuracy claims.
- Famous movies are easier to judge than long-tail movies.
- Some queries have incomplete relevance judgments; an unjudged result is not always wrong.
- Metrics can be improved by overfitting weights to this exact set.
- Latency depends on hardware, database cache state, embedding-model warmup, and whether TMDB fallback runs.
- Runtime TMDB fallback is tested separately because network timing is not deterministic.

The next quality step is collecting anonymous real-user queries and judgments, then keeping a hidden holdout set for weight changes.