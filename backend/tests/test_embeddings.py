from backend.app.services import embeddings


def test_load_embedding_model_prefers_local_cache(monkeypatch):
    calls = []
    model = object()

    def fake_sentence_transformer(model_name, **kwargs):
        calls.append((model_name, kwargs))
        return model

    monkeypatch.setattr(
        embeddings,
        "_get_sentence_transformer_class",
        lambda: fake_sentence_transformer,
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
        "_get_sentence_transformer_class",
        lambda: fake_sentence_transformer,
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

def test_get_embedding_model_loads_once(monkeypatch):
    model = object()
    calls = []

    monkeypatch.setattr(embeddings, "_embedding_model", None)

    def fake_load_embedding_model():
        calls.append("load")
        return model

    monkeypatch.setattr(
        embeddings,
        "_load_embedding_model",
        fake_load_embedding_model,
    )

    assert embeddings.get_embedding_model() is model
    assert embeddings.get_embedding_model() is model
    assert calls == ["load"]


def test_start_embedding_model_preload_uses_daemon_thread(monkeypatch):
    thread_arguments = {}

    class FakeThread:
        def __init__(self, *, target, name, daemon):
            thread_arguments.update(
                target=target,
                name=name,
                daemon=daemon,
            )
            self.started = False

        def start(self):
            self.started = True

    monkeypatch.setattr(embeddings, "Thread", FakeThread)

    thread = embeddings.start_embedding_model_preload()

    assert thread.started is True
    assert thread_arguments == {
        "target": embeddings._preload_embedding_model_safely,
        "name": "embedding-model-preload",
        "daemon": True,
    }
