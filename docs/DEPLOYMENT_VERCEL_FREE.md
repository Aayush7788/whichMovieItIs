# Free Vercel Deployment

## Architecture

- React frontend: Vercel Hobby project with `frontend` as its root directory.
- FastAPI backend: a second Vercel Hobby project with the repository root as its root directory.
- Backend runtime: `Dockerfile.vercel` on Vercel Functions with Fluid compute.
- PostgreSQL and pgvector: Neon Free installed through the Vercel Marketplace.
- Movie posters and runtime metadata: TMDB API and TMDB image CDN.

Vercel containers are stateless, so PostgreSQL cannot run inside the backend
container. Neon remains the persistent database even though it is created and
connected from the Vercel dashboard.

## Why The Production Database Fits

The local database remains complete. The production export keeps all schemas
but excludes existing rows from these experimental tables:

- `movie_search_documents`
- `movie_search_document_embeddings`

The stable `/search` route reads the movie-level search columns in `movies`,
the external identifier mappings in `movie_external_ids`, and the small
`movie_memory_clues` table. The production tables use about `384 MB` in the
current local database. The validated compact restore uses `362 MB`, which fits
under Neon's `0.5 GB` free-project limit with about `150 MB` of headroom.

The two document schemas are still restored empty. This keeps runtime TMDB
imports compatible because newly imported movies can write document rows even
though the historical 42,000-movie document corpus is not uploaded.

## 1. Export The Compact Database

Start the local PostgreSQL container, then run from the repository root:

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe -m scripts.export_production_database
```

Expected output file:

```text
data/processed/whichmovie-production.dump
```

The export script stops before writing the dump if the production tables grow
beyond the configured `450 MB` safety guard.

## 2. Create Neon Through Vercel

1. Open the Vercel dashboard.
2. Create the backend Vercel project from this GitHub repository.
3. Keep the backend project root at the repository root.
4. Open the backend project's Storage or Marketplace page.
5. Install Neon and create a Free PostgreSQL project.
6. Choose a Neon region close to the Vercel function region.
7. Copy the pooled Neon connection string.

Use the pooled connection string for `DATABASE_URL`. Vercel functions can run
concurrently, so the pooled endpoint is safer than opening many direct database
connections.

## 3. Restore The Database To Neon

Set the Neon URL only for the current PowerShell session:

```powershell
$env:NEON_DATABASE_URL="postgresql://USER:PASSWORD@HOST/DB_NAME?sslmode=require"
.\.venv\Scripts\python.exe -m scripts.restore_production_database .\data\processed\whichmovie-production.dump
Remove-Item Env:NEON_DATABASE_URL
```

The restore command enables pgvector, restores the dump, and prints the movie
count and final database size.

## 4. Configure The Backend Vercel Project

Vercel detects `Dockerfile.vercel` at the repository root. The image contains
Python 3.10, the CPU-only PyTorch build, FastAPI, and the cached MiniLM model.

Add these production environment variables:

```text
APP_ENV=production
DATABASE_URL=<pooled Neon connection string>
TMDB_READ_ACCESS_TOKEN=<TMDB read access token>
FRONTEND_ORIGINS=https://YOUR-FRONTEND.vercel.app
PRELOAD_EMBEDDING_MODEL_ON_STARTUP=true
TMDB_RUNTIME_FALLBACK_TIMEOUT_SECONDS=3
TMDB_RUNTIME_FALLBACK_MAX_ATTEMPTS=1
TMDB_RUNTIME_FALLBACK_RATE_LIMIT_WINDOW_SECONDS=60
TMDB_RUNTIME_FALLBACK_MAX_REQUESTS_PER_WINDOW=10
TMDB_RUNTIME_FALLBACK_QUERY_CACHE_SECONDS=1800
VERCEL_SUPPORT_LARGE_FUNCTIONS=1
```

`VERCEL_SUPPORT_LARGE_FUNCTIONS=1` opts an older project into Vercel's large
Function support. Projects created after June 30, 2026 should already have it.

Deploy the backend and note its URL:

```text
https://YOUR-BACKEND.vercel.app
```

## 5. Configure The Frontend Vercel Project

Create a second Vercel project from the same GitHub repository:

1. Set the project root directory to `frontend`.
2. Keep the detected framework as Vite.
3. Add this environment variable:

```text
VITE_API_BASE_URL=https://YOUR-BACKEND.vercel.app
```

Deploy the frontend. Then update `FRONTEND_ORIGINS` in the backend project to
the exact final frontend URL and redeploy the backend.

## 6. Production Smoke Test

```powershell
Invoke-RestMethod https://YOUR-BACKEND.vercel.app/health
Invoke-RestMethod https://YOUR-BACKEND.vercel.app/health/db
Invoke-RestMethod "https://YOUR-BACKEND.vercel.app/search?q=ship%20hits%20iceberg&limit=5"
Invoke-RestMethod "https://YOUR-BACKEND.vercel.app/movies?limit=3&offset=0"
```

Also verify in the browser:

1. The Films page loads movie cards.
2. Rough-plot search returns ranked movies.
3. A movie detail modal opens.
4. An exact title missing locally triggers the TMDB fallback.
5. Vercel backend logs show request latency and fallback usage.

## Free-Tier Constraints

- Neon Free currently allows `0.5 GB` per project, so bulk TMDB imports must be
  limited and database size must be monitored.
- Vercel Hobby functions currently have `2 GB` memory and `1 vCPU`.
- Vercel Hobby Fluid compute includes limited monthly CPU and memory usage.
- The backend can cold-start after scaling to zero; the model is baked into the
  image to avoid downloading from Hugging Face at runtime.
- If free-tier traffic or database storage is exceeded, the architecture can
  remain the same while the Vercel or Neon plan is upgraded.
