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

No researched free managed PostgreSQL provider safely supports the complete
`1.4 GB` database. The selected completely free architecture therefore runs
PostgreSQL with pgvector on the same Oracle Cloud Always Free VM as FastAPI.

The production topology is:

1. Vercel Hobby hosts the React frontend.
2. Oracle Cloud Always Free runs one ARM VM with `2` OCPUs and `12 GB` RAM.
3. Docker Compose runs PostgreSQL with pgvector, FastAPI, and Caddy on that VM.
4. DuckDNS provides the free backend hostname.
5. Caddy terminates HTTPS and keeps ports `5432` and `8000` private.
6. Oracle Object Storage can hold compressed database backups.
7. GitHub Actions provides a manual production deployment workflow.

This architecture keeps the full database instead of deleting the document
tables merely to fit a smaller managed-database quota.

Implementation and provisioning steps are in
`docs/DEPLOYMENT_ORACLE_ALWAYS_FREE.md`.

## Not Recommended

- Full local database upload to Supabase/Neon/Render free tiers.
- Render free Postgres for durable production, because it expires after 30 days.
- Vercel serverless backend for this Python API, because the embedding stack is too large and model loading is not a good serverless fit.
- Exposing PostgreSQL directly to the public internet.
- Treating Oracle trial credits as part of the permanent free architecture.
