# Production Hosting Research

## Current Database Size

- Full local PostgreSQL database: about `1.4 GB`.
- Stable production tables: about `384 MB`.
- Experimental document-search tables: about `1.0 GB`.

The stable production tables are `movies`, `movie_external_ids`, and
`movie_memory_clues`. The large experimental tables are
`movie_search_documents` and `movie_search_document_embeddings`.

## Current Free Hosting Decision

The project can now keep both application layers on Vercel:

1. Vercel Hobby hosts the React frontend.
2. Vercel Hobby deploys FastAPI from `Dockerfile.vercel` as a container-based
   Vercel Function on Fluid compute.
3. Neon Free provides persistent PostgreSQL with pgvector through the Vercel
   Marketplace.
4. TMDB provides runtime title fallback data and poster images.

PostgreSQL is not stored inside the Vercel container because container
instances are stateless. Neon is the persistent database attached to the
backend Vercel project.

## Why This Changed

The previous plan used an Oracle Always Free VM because the complete database
was too large for free managed PostgreSQL and the Python embedding stack was
too large for the old Vercel Function bundle limit.

Vercel added Dockerfile-based HTTP server deployments and large Functions up
to `5 GB` in June 2026. That makes the FastAPI, PyTorch, and MiniLM backend
technically deployable on Vercel. The production database is reduced safely by
excluding historical rows from document-search tables that the stable
`/search` route does not use.

The complete local database is not deleted. The compact export is a separate
production snapshot, and the document table schemas remain available for new
runtime TMDB imports.

## Free Database Comparison

| Provider | Free DB Limit | pgvector | Fit |
| --- | ---: | --- | --- |
| Neon | `0.5 GB` per project | Yes | Selected; production snapshot fits tightly |
| Supabase | `500 MB` database quota | Yes | Similar limit, less headroom flexibility |
| Aiven | Free availability can change | Yes | Not selected |
| Render Postgres | Free database is temporary | Not selected | Not durable enough |

## Important Limits

- The validated compact restore is `362 MB`, leaving about `150 MB` of headroom.
- Runtime TMDB imports must skip weak movies and avoid uncontrolled bulk import.
- Vercel Hobby provides `2 GB` memory and `1 vCPU` for Functions.
- Vercel Hobby Fluid compute includes limited monthly active CPU and memory.
- Container instances scale to zero and cannot hold persistent data locally.

## Runbooks

- Current Vercel and Neon path: `docs/DEPLOYMENT_VERCEL_FREE.md`.
- Oracle VM path retained as a fallback: `docs/DEPLOYMENT_ORACLE_ALWAYS_FREE.md`.

## Primary Sources

- Vercel Dockerfile deployment: https://vercel.com/changelog/bring-your-dockerfile-to-vercel-functions
- Vercel container behavior: https://vercel.com/kb/guide/does-vercel-support-docker-deployments
- Vercel Function limits: https://vercel.com/docs/functions/limitations
- Vercel Function pricing: https://vercel.com/docs/functions/usage-and-pricing
- Neon pricing: https://neon.com/pricing
- Neon pgvector: https://neon.com/docs/extensions/pgvector
