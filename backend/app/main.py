from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException
import psycopg
from .schemas import MovieSearchResponse
from .services.vector_search import search_movies_by_embedding
from .db import get_connection
from .services.hybrid_search import search_movies_hybrid
from .services.reranker import search_movies_reranked
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .services.document_search import search_movies_document_hybrid
from .services.embeddings import preload_embedding_model
from .services.hybrid_v2_search import search_movies_hybrid_v2

logging.basicConfig(
    level=settings.log_level.upper(),
    format=(
        "%(asctime)s %(levelname)s "
        "%(name)s %(message)s"
    ),
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production_settings()

    if settings.preload_embedding_model_on_startup:
        preload_embedding_model()

    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

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
    
    results = search_movies_hybrid(cleaned_query, limit=limit)

    return {
        "query": cleaned_query, 
        "results": results,
    }

@app.get("/search/vector", response_model=MovieSearchResponse)
def vector_search(q: str, limit: int = 5):
    cleaned_query = q.strip()

    if cleaned_query == "":
        raise HTTPException(status_code=400, detail="query cannot be empty")
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 to 20")
    
    result = search_movies_by_embedding(cleaned_query, limit=limit)
    return {
        "query": cleaned_query, 
        "results": result,
    }

@app.get("/search/hybrid", response_model=MovieSearchResponse)
def hybrid_search(q: str, limit: int = 5):
    cleaned_query = q.strip()

    if cleaned_query == "":
        raise HTTPException(status_code=400, detail="query cannot be empty")
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 to 20")
    
    results = search_movies_hybrid(cleaned_query, limit=limit)

    return {
        "query": cleaned_query, 
        "results": results,
    }

@app.get("/search/reranked", response_model=MovieSearchResponse)
def reranked_search(q: str, limit: int = 5):
    cleaned_query = q.strip()

    if cleaned_query == "":
        raise HTTPException(status_code=400, detail="query cannot be empty")
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 to 20")
    
    results = search_movies_reranked(cleaned_query, limit=limit)

    return {
        "query": cleaned_query, 
        "results": results, 
    }


@app.get("/search/documents", response_model=MovieSearchResponse)
def document_search(q: str, limit: int = 5):
    cleaned_query = q.strip()

    if cleaned_query == "":
        raise HTTPException(status_code=400, detail="query cannot be empty")
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 to 20")

    results = search_movies_document_hybrid(
        cleaned_query,
        limit=limit,
    )

    return {
        "query": cleaned_query,
        "results": results,
    }

@app.get("/search/hybrid-v2", response_model=MovieSearchResponse)
def hybrid_v2_search(q: str, limit: int = 5):
    cleaned_query = q.strip()

    if cleaned_query == "":
        raise HTTPException(status_code=400, detail="query cannot be empty")
    if limit < 1 or limit > 20:
        raise HTTPException(status_code=400, detail="limit must be between 1 to 20")

    results = search_movies_hybrid_v2(
        cleaned_query,
        limit=limit,
    )

    return {
        "query": cleaned_query,
        "results": results,
    }
