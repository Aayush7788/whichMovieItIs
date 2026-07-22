import logging
from threading import Lock, Thread

embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
embedding_dimension = 384
embedding_text_max_chars = 4000

_embedding_model = None
_embedding_model_lock = Lock()


def _get_sentence_transformer_class():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer


def _load_embedding_model():
    sentence_transformer = _get_sentence_transformer_class()

    try:
        return sentence_transformer(
            embedding_model_name,
            local_files_only=True,
        )
    except OSError:
        return sentence_transformer(embedding_model_name)


def get_embedding_model():
    global _embedding_model

    if _embedding_model is not None:
        return _embedding_model

    with _embedding_model_lock:
        if _embedding_model is None:
            _embedding_model = _load_embedding_model()

    return _embedding_model

def preload_embedding_model() -> None:
    get_embedding_model()


def is_embedding_model_ready() -> bool:
    return _embedding_model is not None


def _preload_embedding_model_safely() -> None:
    try:
        preload_embedding_model()
    except Exception:
        logging.getLogger(__name__).exception(
            "background embedding model preload failed"
        )


def start_embedding_model_preload() -> Thread:
    thread = Thread(
        target=_preload_embedding_model_safely,
        name="embedding-model-preload",
        daemon=True,
    )
    thread.start()
    return thread

def normalize_text(text: str) -> str:
    return " ".join(text.split())

def build_movie_embedding_text(
    title: str,
    plot_summary: str,
    search_boost_text: str = "",
) -> str:
    text = f"{title}. {plot_summary}. {search_boost_text}"
    return normalize_text(text)[:embedding_text_max_chars]

def _validate_embedding(embedding: list[float]) -> list[float]:
    if len(embedding) != embedding_dimension:
        raise ValueError(
            f"expected embedding dimension {embedding_dimension}, got {len(embedding)}"
        )
    
    return embedding

def embed_text(text: str) -> list[float]:
    embedding = get_embedding_model().encode(
        normalize_text(text), 
        normalize_embeddings=True,

    )
    values = [float(value) for value in embedding.tolist()]
    return _validate_embedding(values)

def embed_texts(texts: list[str]) -> list[list[float]]:
    cleaned_texts = [normalize_text(text) for text in texts]
    
    embeddings = get_embedding_model().encode(
        cleaned_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return [
        _validate_embedding([float(value) for value in embedding.tolist()])
        for embedding in embeddings
    ]

def to_pgvector_literal(embedding: list[float]) -> str:
    _validate_embedding(embedding)
    return "[" + ",".join(str(float(value)) for value in embedding) + "]"

