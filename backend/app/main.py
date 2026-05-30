from fastapi import FastAPI, HTTPException
import psycopg
from .schemas import MovieSearchResponse
from .services.search import search_movies
from .db import get_connection
app = FastAPI()

@app.get("/health")
def health():
    return {
        "status": "ok"
    }

@app.get("/health/db")
def health_db():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                   "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
                )
                row = cur.fetchone()
    except psycopg.Error as e:
        raise HTTPException(status_code=503, detail=str(e))
    return{
        "database": "ok",
        "pgvector": row[0] if row else None,
    }

@app.get("/search", response_model=MovieSearchResponse)
def search(q:str, limit: int = 5):
    cleaned_query = q.strip()

    if cleaned_query == "":
        raise HTTPException(status_code=400, detail="query cannot be empty")
    if limit< 1 or limit>20:
        raise HTTPException(status_code=400, detail="limit must be between 1 to 20")
    
    results = search_movies(cleaned_query, limit=limit)

    return {
        "query": cleaned_query, 
        "results": results,
    }