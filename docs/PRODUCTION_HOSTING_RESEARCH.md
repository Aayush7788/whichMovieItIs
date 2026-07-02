# Production Hosting Research

## Current Database Size

- Full local PostgreSQL database: about `1.4 GB`.
- Lean production-critical tables for current stable `/search`:
  - `movies`
  - `movie_external_ids`
  - `movie_memory_clues`
- Lean production-critical table size: about `380 MB`.
- Document-search experimental tables add about `1.0 GB`:
  - `movie_search_documents`
  - `movie_search_document_embeddings`

## Free Database Findings

| Provider | Free DB Limit | pgvector | Production Fit |
| --- | ---: | --- | --- |
| Supabase | `500 MB` database quota before read-only mode | Yes | Lean production DB may fit, full `1.4 GB` DB does not fit |
| Neon | `0.5 GB` storage per free project | Yes | Lean production DB may fit tightly, full DB does not fit |
| Aiven | `1 GB` storage, `1 GB` RAM, `1 CPU` | Yes | Lean production DB fits, full DB does not fit |
| Render Postgres | `1 GB`, expires after `30 days` | Unknown for final use | Not suitable for durable production data |

Sources:

- Supabase database size docs: https://supabase.com/docs/guides/platform/database-size
- Supabase pgvector docs: https://supabase.com/docs/guides/database/extensions/pgvector
- Neon pricing: https://neon.com/pricing
- Neon pgvector docs: https://neon.com/docs/extensions/pgvector
- Aiven free PostgreSQL: https://aiven.io/free-postgresql-database
- Aiven pgvector: https://aiven.io/blog/aiven-for-postgres-supports-pgvector
- Render free limits: https://render.com/docs/free

## Decision

No researched free managed Postgres option safely supports the full current
`1.4 GB` database as a durable production database.

For a free public deployment, the practical path is:

1. Deploy only the lean production database first.
2. Keep stable `/search` on movie-level hybrid search.
3. Keep `/search/documents` and document embeddings out of the first production database.
4. Keep runtime TMDB exact-title import enabled.
5. Avoid large TMDB bulk import until there is paid database storage or a reliable free provider with enough capacity.

## Recommended First Attempt

Try Aiven free PostgreSQL first because its `1 GB` storage limit gives more
headroom than Supabase or Neon for the lean production database.

If Aiven free is too unstable or inactive-sleeps too aggressively, try Supabase
with the lean production database and strict catalog limits.

## Not Recommended

- Full local database upload to Supabase/Neon/Render free tiers.
- Render free Postgres for durable production, because it expires after 30 days.
- Vercel serverless backend for this Python API, because the embedding stack is too large and model loading is not a good serverless fit.
