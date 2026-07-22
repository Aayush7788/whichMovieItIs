# Production Smoke Results

## Final Release Verification - 2026-07-22

### Public Application

- Live URL: https://whichmovieitis.vercel.app
- Verified Vercel deployment: dpl_81YaSu5ehqBV7QJdZpn3Ki5vm3kJ
- Region: iad1
- Deployment state: READY
- Application code commit: c4f0f42dd3f94d01c7e046fe81fda033b45e3a14

### Automated Release Gate

- Python Ruff: passed for backend and scripts.
- Backend tests: 64 passed, 2 skipped.
- Frontend ESLint: passed.
- Frontend production build: passed with Vite 8.0.14.
- Production bundle: 205.90 kB JavaScript and 10.98 kB CSS before gzip.
- Production backend Docker image: built successfully.
- Local release container: health OK, embedding model ready, experimental hybrid-v2 route not exposed.
- GitHub Actions: successful for both backend and frontend jobs.

### Production API

- GET /api/health: 200, status ok.
- GET /api/health/db: 200, database ok, pgvector 0.8.1.
- GET /api/health/search: reports warming during model load and ready afterward.
- GET /api/movies?limit=1&offset=0: total 42,601 before the fallback test.
- GET /api/search?q=ship%20hits%20iceberg&limit=5: first result A Night to Remember.
- GET /api/search/hybrid-v2: 404, confirming only stable production search is public.
- Homepage responses include Content-Security-Policy, X-Content-Type-Options, and X-Frame-Options.

The measured first search after deployment took 5,944 ms while the model was still
warming. The immediate warm search took 476 ms. Free-tier cold starts are therefore
visible to the user but cannot be guaranteed below three seconds.

### Live TMDB Fallback

- Smoke query: OK! Madam: Bon Voyage.
- The title was confirmed absent from Neon before the request.
- Request latency: 3,257 ms end to end.
- First result: exact title match.
- Imported TMDB movie ID: 1307247.
- Persisted movie key: tmdb:1307247.
- Overview length: 171 characters, above the 80-character quality gate.
- Movie embedding: created synchronously.
- Production document tables: remained empty.
- Catalog after fallback: 42,602 movies with zero missing movie embeddings.

### Production Browser QA

The final Playwright browser pass verified:

- Desktop homepage loaded with the catalog.
- Films navigation scrolled to the catalog.
- Load more increased rendered movie cards from 24 to 42.
- Movie detail modal opened and closed correctly.
- Rough-memory query red pill blue pill ranked The Matrix first.
- Mobile layout at 390 by 844 had no horizontal overflow.
- Favicon loaded successfully after the QA fix.
- Console errors: zero.
- Page errors: zero.
- Failed requests: zero.
- HTTP responses at or above 400: zero.

### Production Database

- PostgreSQL: 18.4.
- pgvector: 0.8.1.
- Database size: approximately 362 MB.
- Storage guard: 450 MB.
- Production audit: PASS.
- First verified compressed backup: 118.8 MB.
- Backup archive: 115 readable pg_restore entries.
- Backup path is ignored by Git under data/processed/backups/.

### Stable Hybrid Metrics

- hit@5 = 1.0000
- mrr@10 = 0.9285
- recall@10 = 0.9593
- ndcg@10 = 0.8859
- no_result = 1.0000
- average latency = 406.0909 ms
- p95 latency = 930.2597 ms

These retrieval metrics cover the maintained 50-case evaluation set: 45 ranked
queries and five no-result queries. Production network and cold-start latency are
reported separately above.
