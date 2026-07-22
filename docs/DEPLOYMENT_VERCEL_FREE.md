# Free Vercel Deployment

## Production Architecture

WhichMovieItIs deploys as one Vercel project and one public domain:

~~~text
https://YOUR-PROJECT.vercel.app
├── /                         React and Vite frontend
├── /api/health               FastAPI process health
├── /api/health/db            PostgreSQL and pgvector health
├── /api/search               Stable hybrid movie search
├── /api/movies               Paginated movie catalog
├── /api/movies/{movie_key}   Movie details
└── /api/docs                 FastAPI documentation
~~~

The root vercel.json defines two Vercel Services:

- frontend: built from frontend/
- backend: built from backend/Dockerfile.vercel

Ordered rewrites send /api/* to the backend container and all remaining
requests to the frontend. PostgreSQL remains external because Vercel
containers are stateless.

## Current Repository Preparation

The repository already contains:

- vercel.json: one-project Services routing
- vercel.json frontend service fields: Vite build and cross-platform local development configuration
- backend/Dockerfile.vercel: Python, CPU PyTorch, and cached MiniLM model
- backend/requirements.vercel.txt: production-only Python dependencies
- frontend/scripts/vercel-dev.mjs: reads Vercel's dynamic PORT correctly on Windows
- .vercelignore: excludes local datasets, dumps, caches, and build outputs
- scripts/export_production_database.py: compact production export
- scripts/restore_production_database.py: pgvector-aware restore
- /api/* FastAPI routes and a 450 MB TMDB persistence guard

Do not commit a database URL, TMDB token, .env, or production dump.

## 1. Validate Locally

From the repository root:

~~~powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q

Push-Location frontend
npm.cmd run lint
npm.cmd run build
Pop-Location
~~~

Validate the backend image while Docker Desktop is running:

~~~powershell
docker build -f backend\Dockerfile.vercel -t whichmovie-vercel backend
~~~

The image downloads sentence-transformers/all-MiniLM-L6-v2 during the build
and runs with Hugging Face offline mode enabled afterward.

## 2. Export the Compact Production Database

Start the local database:

~~~powershell
docker compose up -d db
~~~

Create the compact dump:

~~~powershell
.\.venv\Scripts\python.exe -m scripts.export_production_database --output .\data\processed\whichmovie-production.dump --max-size-mb 150
~~~

The dump keeps the production search tables and schema but excludes historical
rows from the experimental document-search tables. The dump must remain
ignored by Git.

## 3. Create the Neon Database

1. Create a Neon Free project.
2. Choose a region near the Vercel function region.
3. Open the project's connection details.
4. Copy the direct connection string for restore operations.
5. Copy the pooled connection string for the deployed application.
6. Ensure both URLs include TLS settings such as sslmode=require.

Use the direct URL only while restoring:

~~~powershell
.\.venv\Scripts\python.exe -m scripts.restore_production_database .\data\processed\whichmovie-production.dump --database-url "<NEON_DIRECT_DATABASE_URL>"
~~~

In the Neon SQL editor, verify:

~~~sql
select extversion
from pg_extension
where extname = 'vector';

select count(*) as movies
from movies;

select count(*) as movie_embeddings
from movies
where search_embedding is not null;

select pg_size_pretty(pg_database_size(current_database()))
as database_size;
~~~

Expected conditions:

- pgvector is installed.
- The catalog contains approximately 42,000 or more movies.
- Production movie embeddings exist.
- Total size remains below Neon's free storage limit.

## 4. Create the Vercel Project

1. Sign in to Vercel with GitHub.
2. Select Add New Project.
3. Import the WhichMovieItIs repository.
4. Keep the project root at the repository root.
5. Set the project name to whichmovieitis.
6. If unavailable, use which-movie-it-is or another close name.
7. Under Build and Deployment settings, set Framework Preset to Services.
8. Do not change the service roots defined in vercel.json.

The exact .vercel.app project name is first-come, first-served.

## 5. Configure Production Environment Variables

Add these variables to the Vercel project's Production environment:

~~~text
APP_ENV=production
DATABASE_URL=<NEON_POOLED_DATABASE_URL>
TMDB_READ_ACCESS_TOKEN=<TMDB_READ_ACCESS_TOKEN>
FRONTEND_ORIGINS=https://YOUR-PROJECT.vercel.app
LOG_LEVEL=INFO

TMDB_RUNTIME_FALLBACK_TIMEOUT_SECONDS=3
TMDB_RUNTIME_FALLBACK_MAX_ATTEMPTS=1
TMDB_RUNTIME_FALLBACK_RATE_LIMIT_WINDOW_SECONDS=60
TMDB_RUNTIME_FALLBACK_MAX_REQUESTS_PER_WINDOW=10
TMDB_RUNTIME_FALLBACK_QUERY_CACHE_SECONDS=1800
TMDB_RUNTIME_PERSISTENCE_MAX_DATABASE_MB=450

PRELOAD_EMBEDDING_MODEL_ON_STARTUP=true
~~~

Use the pooled Neon URL for DATABASE_URL. Set FRONTEND_ORIGINS to the exact
final Vercel origin without a trailing slash.

For older Vercel projects that do not automatically support large Functions,
also add:

~~~text
VERCEL_SUPPORT_LARGE_FUNCTIONS=1
~~~

No VITE_API_BASE_URL is required because the browser uses same-origin
/api requests.

## 6. Deploy

Deploy through the Git integration by pushing the prepared commit to GitHub.
Vercel builds both services in one deployment.

Alternatively, after linking the project with the Vercel CLI:

~~~powershell
npx.cmd vercel@latest pull --yes
npx.cmd vercel@latest build --prod
npx.cmd vercel@latest deploy --prebuilt --prod
~~~

The first backend build is expected to take longer because it installs CPU
PyTorch and downloads the embedding model.

## 7. Production Smoke Test

Replace YOUR-PROJECT with the deployed project name:

~~~powershell
$baseUrl = "https://YOUR-PROJECT.vercel.app"

Invoke-RestMethod "$baseUrl/api/health"
Invoke-RestMethod "$baseUrl/api/health/db"
Invoke-RestMethod "$baseUrl/api/movies?limit=3&offset=0"
Invoke-RestMethod "$baseUrl/api/search?q=ship%20hits%20iceberg&limit=5"
~~~

Open these URLs in a browser:

~~~text
https://YOUR-PROJECT.vercel.app/
https://YOUR-PROJECT.vercel.app/api/docs
~~~

Verify:

1. The homepage and Films catalog load.
2. Rough-plot search returns ranked local movies.
3. Movie cards open the correct details.
4. Posters load and missing posters use the frontend fallback.
5. A locally missing exact title invokes TMDB.
6. Vercel Runtime Logs show search latency and fallback decisions.
7. Browser developer tools show no CORS or mixed-content errors.

## 8. Storage-Guard Behavior

Before inserting a new runtime TMDB movie, the backend checks:

~~~sql
select pg_database_size(current_database());
~~~

Behavior:

- Below 450 MB: save the TMDB movie, embedding, identifiers, and searchable
  documents.
- At or above 450 MB: return the fetched movie for the current request but do
  not persist it.
- Existing TMDB-linked movies may still be updated because they do not create a
  new catalog row.
- Every skipped persistence attempt writes a warning to Vercel Runtime Logs.

The guard protects free-tier headroom but is not a replacement for monitoring
the Neon dashboard.

## Troubleshooting

### Vercel returns frontend 404 pages for /api/*

Confirm the project Framework Preset is Services, then redeploy. The
multi-service configuration is not active if the project is not configured for
Services.

### Backend fails during startup

Check Vercel Runtime Logs for production-setting validation. Confirm
DATABASE_URL, TMDB_READ_ACCESS_TOKEN, and FRONTEND_ORIGINS are present.

### /api/health/db returns 503

Confirm the pooled Neon URL is correct, TLS is enabled, and the restored
database contains pgvector.

### Backend build exceeds package limits

Confirm the project supports large Functions. Add
VERCEL_SUPPORT_LARGE_FUNCTIONS=1 for an older project and redeploy.

### Search is slow after inactivity

The backend can cold-start after scaling to zero. The model is stored inside
the image to avoid a network download, but loading Python, PyTorch, the model,
and a database connection can still make a cold request slower than a warm
request.

## Platform References

- Vercel Services: https://vercel.com/kb/guide/vercel-services
- Vercel Docker containers: https://vercel.com/blog/dockerfile-on-vercel
- Vercel Function limits: https://vercel.com/docs/functions/limitations
- Vercel environment variables: https://vercel.com/docs/environment-variables
- Neon pricing: https://neon.com/pricing
- Neon pgvector: https://neon.com/docs/extensions/pgvector
