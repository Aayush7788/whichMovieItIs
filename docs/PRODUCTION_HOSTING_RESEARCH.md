# Production Hosting Research

## Selected Architecture

The selected free-first deployment architecture is:

| Component | Platform | Reason |
|---|---|---|
| React and Vite frontend | Vercel Service | Static delivery and Git previews |
| FastAPI backend | Vercel container Service | Supports Python, PyTorch, MiniLM, and one shared domain |
| PostgreSQL and pgvector | Neon Free | Persistent managed PostgreSQL with vector support |
| Posters and new-title metadata | TMDB API and CDN | Existing project integration |

Both application services deploy inside one Vercel project. Ordered rewrites
route /api/* to the FastAPI container and all other paths to the frontend.
The database remains in Neon because Vercel containers are stateless.

## Why the Database Fits

The original local database included historical document-search rows that are
not required by the stable production hybrid route. The compact production
export retains the core catalog, movie embeddings, full-text indexes, external
IDs, and small production clue table while leaving the experimental document
tables empty.

The previously validated compact restore was approximately 362 MB. This fits
inside Neon's 0.5 GB free-project storage limit, but headroom is tight.

Runtime TMDB persistence is therefore guarded at 450 MB:

- below the threshold, eligible missing titles can be persisted;
- at or above the threshold, the current TMDB result is returned without a
  database write;
- bulk TMDB ingestion is not part of the initial free deployment.

## Operational Constraints

- Vercel Services and container Functions use Fluid compute and can scale to
  zero.
- Cold requests may be slower than warm requests even though MiniLM is baked
  into the backend image.
- Vercel containers cannot persist local files between instances.
- Neon connection pooling must be used by the deployed application.
- Database size and Vercel usage must be monitored in their dashboards.
- Search evaluation metrics describe the maintained judged query set, not
  universal accuracy.

## Deployment Runbook

Use docs/DEPLOYMENT_VERCEL_FREE.md for the executable deployment and smoke-test
process.

## Primary Sources

- Vercel Services: https://vercel.com/kb/guide/vercel-services
- Vercel containers: https://vercel.com/blog/dockerfile-on-vercel
- Vercel Function limits: https://vercel.com/docs/functions/limitations
- Vercel Function usage: https://vercel.com/docs/functions/usage-and-pricing
- Neon pricing: https://neon.com/pricing
- Neon pgvector: https://neon.com/docs/extensions/pgvector
