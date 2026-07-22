import psycopg
from fastapi import APIRouter, HTTPException

from .db import get_connection
from .schemas import (
    MovieCatalogResponse,
    MovieDetail,
    MovieSearchResponse,
)
from .services.embeddings import is_embedding_model_ready
from .services.hybrid_search import search_movies_hybrid
from .services.movies import get_movie_detail, list_movies


api_router = APIRouter(prefix="/api")
maximum_search_query_length = 1000


@api_router.get("/health")
def health():
    return {"status": "ok"}


@api_router.get("/health/db")
def health_db():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "select extversion from pg_extension "
                    "where extname = 'vector';"
                )
                row = cursor.fetchone()
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {
        "database": "ok",
        "pgvector": row[0] if row else None,
    }


@api_router.get("/health/search")
def health_search():
    return {
        "status": "ready" if is_embedding_model_ready() else "warming",
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
def search(q: str, limit: int = 5):
    cleaned_query = q.strip()

    if not cleaned_query:
        raise HTTPException(
            status_code=400,
            detail="query cannot be empty",
        )

    if len(cleaned_query) > maximum_search_query_length:
        raise HTTPException(
            status_code=400,
            detail=(
                "query cannot exceed "
                f"{maximum_search_query_length} characters"
            ),
        )

    if limit < 1 or limit > 20:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 20",
        )

    return {
        "query": cleaned_query,
        "results": search_movies_hybrid(cleaned_query, limit=limit),
    }