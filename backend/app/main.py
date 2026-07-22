from contextlib import asynccontextmanager
import logging

from fastapi import APIRouter, FastAPI, HTTPException
import psycopg
from .schemas import (
    MovieCatalogResponse,
    MovieDetail,
    MovieSearchResponse,
)
from .services.vector_search import search_movies_by_embedding
from .db import get_connection
from .services.hybrid_search import search_movies_hybrid
from .services.reranker import search_movies_reranked
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .services.document_search import search_movies_document_hybrid
from .services.embeddings import start_embedding_model_preload
from .services.hybrid_v2_search import search_movies_hybrid_v2
from .services.movies import get_movie_detail, list_movies

logging.basicConfig(
    level=settings.log_level.upper(),
    format=(
        "%(asctime)s %(levelname)s "
        "%(name)s %(message)s"
    ),
)
for logger_name in (
    "httpx",
    "httpcore",
    "huggingface_hub",
    "sentence_transformers",
):
    logging.getLogger(logger_name).setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production_settings()

    if settings.preload_embedding_model_on_startup:
        app.state.embedding_preload_thread = start_embedding_model_preload()

    yield


app = FastAPI(
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
    swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect",
)
api_router = APIRouter(prefix="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@api_router.get("/health")
def health():
    return {
        "status": "ok"
    }

@api_router.get("/health/db")
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

@api_router.get("/movies", response_model=MovieCatalogResponse)
def movies(limit: int = 24, offset: int = 0):
    if limit < 1 or limit > 60:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 60",
        )
    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail="offset must be greater than or equal to 0",
        )

    return list_movies(limit=limit, offset=offset)

@api_router.get("/movies/{movie_key}", response_model=MovieDetail)
def movie_detail(movie_key: str):
    movie = get_movie_detail(movie_key)

    if movie is None:
        raise HTTPException(
            status_code=404,
            detail="movie not found",
        )

    return movie

@api_router.get("/search", response_model=MovieSearchResponse)
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

@api_router.get("/search/vector", response_model=MovieSearchResponse)
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

@api_router.get("/search/hybrid", response_model=MovieSearchResponse)
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

@api_router.get("/search/reranked", response_model=MovieSearchResponse)
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


@api_router.get("/search/documents", response_model=MovieSearchResponse)
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

@api_router.get("/search/hybrid-v2", response_model=MovieSearchResponse)
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

app.include_router(api_router)
