# Production Smoke Results

## 2026-07-02

### Git State

- Branch: `main`
- Latest production-hardening commits:
  - `Record production readiness decisions`
  - `Add production search fallback logging`
  - `Enforce runtime TMDB fallback budget`
  - `Add production environment validation`
  - `Add backend production Dockerfile`
  - `Document free production database options`

### Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
cd frontend
npm.cmd run lint
npm.cmd run build
.\.venv\Scripts\python.exe -m scripts.evaluate_search --mode hybrid
```

### Results

- Backend tests: `38 passed, 2 skipped`.
- Frontend lint: passed.
- Frontend production build: passed.
- `/health`: `200`.
- `/health/db`: `200`, pgvector `0.8.2`.
- Local `/search` smoke query: `The Matrix`.
- Runtime TMDB fallback smoke query: `M3GAN 2.0`.
- Runtime TMDB fallback request latency: about `2804 ms`.
- Runtime TMDB fallback imported `M3GAN 2.0` as TMDB movie `1071585`.

### Current Hybrid Metrics

- `hit@5=1.0000`
- `mrr@10=0.9063`
- `recall@10=0.9593`
- `ndcg@10=0.8850`
- `no_result=1.0000`
- `avg_latency_ms=591.4617`
- `p95_latency_ms=1310.7650`

### Current Database Counts

- Movies: `42,577`
- TMDB-only movies: `370`
- Runtime-imported movies: `5`
- Missing movie embeddings: `0`
- Missing document embeddings: `7`

### Notes

- The first request in a fresh process still pays model startup cost unless the backend host keeps the process warm.
- The measured runtime fallback request was under the approved `3s` target after FastAPI startup preload.
- The first free-cloud production database should use the lean production table set, not the full document-search database.
