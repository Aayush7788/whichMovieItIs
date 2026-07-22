from backend.app.services import reranker


def test_get_reranker_model_loads_lazily_once(monkeypatch):
    model = object()
    calls = []

    def fake_cross_encoder(model_name):
        calls.append(model_name)
        return model

    monkeypatch.setattr(
        reranker,
        "_get_cross_encoder_class",
        lambda: fake_cross_encoder,
    )
    reranker.get_reranker_model.cache_clear()

    try:
        assert reranker.get_reranker_model() is model
        assert reranker.get_reranker_model() is model
    finally:
        reranker.get_reranker_model.cache_clear()

    assert calls == [reranker.reranker_model_name]
