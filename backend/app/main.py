from fastapi import FastAPI, HTTPException
import psycopg
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