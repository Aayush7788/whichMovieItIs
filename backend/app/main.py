from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .config import settings
from .http_middleware import ProductionHttpMiddleware
from .services.embeddings import start_embedding_model_preload


logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.add_middleware(ProductionHttpMiddleware)
app.include_router(api_router)