param(
    [ValidateSet("audit", "recent", "popular", "backup")]
    [string]$Mode = "audit",
    [int]$Limit = 25,
    [int]$MaxDatabaseSizeMb = 450
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Python virtual environment not found: $Python"
}

Push-Location $ProjectRoot

try {
    & $Python -m scripts.audit_production_database --max-size-mb $MaxDatabaseSizeMb

    if ($Mode -eq "recent" -or $Mode -eq "popular") {
        & $Python -m scripts.import_tmdb_movies --source discover --discover-mode $Mode --limit $Limit --max-database-size-mb $MaxDatabaseSizeMb
        & $Python -m scripts.backfill_movie_embeddings --limit $Limit
        & $Python -m scripts.audit_production_database --max-size-mb $MaxDatabaseSizeMb
    }

    if ($Mode -eq "backup") {
        & $Python -m scripts.backup_production_database
    }
}
finally {
    Pop-Location
}