# Local Setup

This guide creates the local development environment and explains which data steps are required for the stable product.

## Prerequisites

- Windows PowerShell
- Python 3.10
- Node.js and `npm.cmd`
- Docker Desktop
- TMDB API read-access token
- Authorized CMU Movie Summary Corpus files

Run every Python module command from the repository root. This keeps `backend` importable and avoids `ModuleNotFoundError: No module named 'backend'`.

## 1. Install Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

cd frontend
npm.cmd install
cd ..
```

## 2. Configure Environment

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set:

```dotenv
TMDB_READ_ACCESS_TOKEN=your_tmdb_read_access_token
```

The checked-in local PostgreSQL defaults match `docker-compose.yml`.

## 3. Start PostgreSQL

```powershell
docker compose up -d db
docker compose ps
```

The container exposes PostgreSQL on local port `15432`.

## 4. Create Schema

Run schema creation before any loader:

```powershell
.\.venv\Scripts\python.exe -m scripts.create_movie_table
```

This creates pgvector, movie tables, generated full-text columns, and indexes.

## 5. Prepare CMU Data

Place source files under:

```text
data/raw/MovieSummaries/MovieSummaries/movie.metadata.tsv
data/raw/MovieSummaries/MovieSummaries/plot_summaries.txt
data/raw/MovieSummaries/MovieSummaries/character.metadata.tsv
data/raw/corenlp_plot_summaries/corenlp_plot_summaries/
```

Build the full JSONL catalog:

```powershell
.\.venv\Scripts\python.exe -m scripts.build_cmu_processed `
  --limit 0 `
  --include-non-us-english `
  --output data\processed\cmu_movies_full.jsonl
```

Load movie rows:

```powershell
.\.venv\Scripts\python.exe -m scripts.load_cmu_movies `
  --input data\processed\cmu_movies_full.jsonl
```

Build plot, character/cast, and CoreNLP search documents:

```powershell
.\.venv\Scripts\python.exe -m scripts.cmu_search_document `
  --input data\processed\cmu_movies_full.jsonl
```

## 6. Build Required Movie Embeddings

The stable semantic branch reads `movies.search_embedding`. Backfill it for every movie:

```powershell
.\.venv\Scripts\python.exe -m scripts.backfill_movie_embeddings
```

Document embeddings are not required by the stable three-branch search. Build them only when running document-level experiments:

```powershell
.\.venv\Scripts\python.exe -m scripts.backfill_search_document_embeddings
```

## 7. Add TMDB Posters and Metadata

Enrich CMU rows in controlled batches:

```powershell
.\.venv\Scripts\python.exe -m scripts.enrich_tmdb_metadata --limit 100
```

Use `--limit 0` only when intentionally processing every pending movie. The script updates metadata and source mappings without replacing the richer CMU plot summary.

Optional catalog growth:

```powershell
# Popular titles
.\.venv\Scripts\python.exe -m scripts.import_tmdb_movies `
  --source discover `
  --discover-mode popular `
  --page-start 1 `
  --page-end 5 `
  --limit 100

# Recent releases
.\.venv\Scripts\python.exe -m scripts.import_tmdb_movies `
  --source discover `
  --discover-mode recent `
  --page-start 1 `
  --page-end 5 `
  --limit 100

# TMDB change feed
.\.venv\Scripts\python.exe -m scripts.import_tmdb_movies `
  --source changes `
  --limit 100
```

The default quality filter skips movies whose overview is shorter than 80 characters.

## 8. Start the Complete App

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_local.ps1
```

Services:

- frontend: `http://127.0.0.1:5173`
- backend: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- PostgreSQL: `127.0.0.1:15432`

Stop managed processes and the database:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\stop_local.ps1 -StopDatabase
```

## 9. Verify Health

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/db
Invoke-RestMethod "http://127.0.0.1:8000/search?q=red%20pill%20blue%20pill&limit=5"
Invoke-RestMethod "http://127.0.0.1:8000/movies?limit=5&offset=0"
```

## 10. Inspect PostgreSQL

Open psql inside the Docker container:

```powershell
docker exec -it whichmovie-postgres psql -U postgres -d whichmovie
```

Useful psql commands:

```sql
\dt
\d movies
\d movie_external_ids
\d movie_search_documents

SELECT count(*) FROM movies;
SELECT * FROM movies LIMIT 5;
SELECT * FROM movie_external_ids LIMIT 5;
SELECT * FROM movie_search_documents LIMIT 5;
SELECT * FROM movie_search_document_embeddings LIMIT 5;
```

Exit with `\q`.

## Troubleshooting

### Backend import error

Wrong:

```powershell
python.exe .\scripts\load_cmu_movies.py
```

Correct, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m scripts.load_cmu_movies
```

### Missing table

Run schema creation before loaders:

```powershell
.\.venv\Scripts\python.exe -m scripts.create_movie_table
```

### Port 8000 is blocked

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

Stop the owning process only after confirming it belongs to an old local backend, or start Uvicorn on another port and update the Vite proxy.

### Frontend proxy shows ECONNREFUSED

The frontend is running but FastAPI is not listening on `127.0.0.1:8000`. Start the backend or run `scripts/start_local.ps1` so both services start together.