# Production Readiness Decisions

## Round 1 - Product Direction

- Production goal: public deployed app.
- Rough-plot search scope: support the current 42k+ movie catalog first; TMDB rough-plot support is desirable if the imported TMDB text quality is good enough.
- TMDB catalog strategy: popular, recent, filtered import instead of importing every TMDB movie.
- Runtime TMDB fallback: if a particular movie is not in the local database, TMDB import should happen.
- Deployment preference: Vercel/free deployment if practical.

## Round 2 - Runtime Fallback and Operations

- Runtime TMDB fallback scope: trigger only when the query looks like a movie title, not for rough-plot queries.
- Hosting/cost preference: everything should be free where possible, but selected carefully for the best free option.
- Daily import operation: manual command triggered by the developer, not automatic scheduled worker for now.
- Acceptable runtime TMDB import wait time: under 3 seconds.
- Experimental endpoints: do not remove `/search/hybrid-v2`, `/search/documents`, or `/search/reranked` yet.

## Round 3 - Free Hosting and Catalog Limits

- Backend deployment: prefer everything free; if another backend platform has a free tier, it can be used, otherwise prefer Vercel where practical.
- Database deployment: use Supabase free Postgres if it can support the current ~1.5 GB database and required performance; otherwise keep Docker/Postgres.
- TMDB catalog size: limit imports to stay inside free database limits.
- TMDB import policy: do not bulk-import unnecessary movies; import TMDB movies mainly when the local database does not have the title and runtime fallback/search needs it.
- Daily import size: avoid large daily bulk imports for now; follow the database-limit and missing-title import strategy.
- Search priority: search reliability is more important than catalog size.
- TMDB quality filter: skip low-quality TMDB movies with missing or weak overview text.

## Round 4 - Deployment Architecture

- Production architecture: Vercel frontend plus a free backend host plus a free Postgres/pgvector database.
- Cloud database requirement: prefer a free cloud database that can handle the current ~1.5 GB database.
- Initial production catalog: include the current 42k CMU movies, TMDB posters/metadata, and runtime TMDB exact-title import.
- TMDB bulk import: avoid additional large TMDB bulk imports for initial production.
- TMDB-only rough-plot quality: acceptable if rough-plot search is weaker for runtime-imported TMDB-only movies because TMDB overviews are shorter than CMU summaries.
- Public URL: free platform URL is acceptable first; custom domain is not required now.

## Round 5 - Production Behavior

- Runtime TMDB import behavior: keep synchronous runtime TMDB import under 3 seconds.
- Runtime TMDB import filter: any movie can be imported; do not require overview, poster, non-adult flag, English language, or popularity threshold for runtime fallback.
- Additional health endpoint: do not add `/health/search` now.
- Search logging: print logs to backend console for now instead of writing search activity to a database table.
- Product goal: real user-ready product, not only a resume/demo project.

## Final Deployment Decision

- Public surface: one Vercel project and one domain.
- Frontend: React and Vite Vercel Service at normal paths.
- Backend: FastAPI container Service at /api/*.
- Database: compact Neon PostgreSQL and pgvector restore.
- Runtime catalog growth: exact-title TMDB fallback, with persistence blocked at
  450 MB and transient return preserved above the limit.
- Deployment is not considered complete until the Neon restore and public smoke
  test pass.
