# Production Smoke Results

## Latest Local Verification — 2026-07-22

### Commands

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q

cd frontend
npm.cmd run lint
npm.cmd run build
cd ..

.\.venv\Scripts\python.exe -m scripts.evaluate_search --mode hybrid
```

### Automated Results

- Backend tests: `48 passed, 2 skipped`.
- Frontend ESLint: passed.
- Frontend production build: passed with Vite 8.0.14.
- Production bundle: 205.39 kB JavaScript and 10.88 kB CSS before gzip.

### Live Local API

- `GET /health`: `200`, status `ok`.
- `GET /health/db`: `200`, database `ok`, pgvector `0.8.2`.
- `GET /movies?limit=1&offset=0`: total `42,601` movies.
- `GET /search?q=red%20pill%20blue%20pill&limit=5`: first result `The Matrix`.

### Stable Hybrid Metrics

- `hit@5=1.0000`
- `mrr@10=0.9285`
- `recall@10=0.9593`
- `ndcg@10=0.8859`
- `no_result=1.0000`
- `avg_latency_ms=406.0909`
- `p95_latency_ms=930.2597`

These metrics cover 50 maintained evaluation cases: 45 ranked queries and five no-result queries.

## Runtime TMDB Fallback Verification — 2026-07-02

- Smoke query: `M3GAN 2.0`.
- Request latency: approximately `2804 ms`.
- Imported TMDB movie ID: `1071585`.
- The request completed under the configured three-second fallback target after startup embedding-model preload.

This network-dependent fallback was not repeated during the 2026-07-22 documentation pass to avoid adding another movie solely for a smoke test.

## Deployment Status

- The compact production-database export and Vercel configuration are prepared.
- The product is verified locally.
- No public deployment URL is claimed yet.