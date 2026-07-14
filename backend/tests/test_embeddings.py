from backend.app.services import embeddings


def test_load_embedding_model_prefers_local_cache(monkeypatch):
    calls = []
    model = object()

    def fake_sentence_transformer(model_name, **kwargs):
        calls.append((model_name, kwargs))
        return model

    monkeypatch.setattr(
        embeddings,
        "SentenceTransformer",
        fake_sentence_transformer,
    )

    assert embeddings._load_embedding_model() is model
    assert calls == [
        (
            embeddings.embedding_model_name,
            {"local_files_only": True},
        ),
    ]


def test_load_embedding_model_downloads_when_cache_is_missing(
    monkeypatch,
):
    calls = []
    model = object()

    def fake_sentence_transformer(model_name, **kwargs):
        calls.append((model_name, kwargs))

        if kwargs.get("local_files_only"):
            raise OSError("model is not cached")

        return model

    monkeypatch.setattr(
        embeddings,
        "SentenceTransformer",
        fake_sentence_transformer,
    )

    assert embeddings._load_embedding_model() is model
    assert calls == [
        (
            embeddings.embedding_model_name,
            {"local_files_only": True},
        ),
        (
            embeddings.embedding_model_name,
            {},
        ),
    ]
