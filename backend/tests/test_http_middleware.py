from fastapi.testclient import TestClient

from backend.app import api as api_module
from backend.app.config import settings
from backend.app.main import app
from backend.app.services.rate_limit import api_rate_limiter


client = TestClient(app)


def test_api_responses_include_security_headers():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == (
        "strict-origin-when-cross-origin"
    )


def test_search_rate_limit_returns_429(monkeypatch):
    api_rate_limiter.clear()
    monkeypatch.setattr(
        settings,
        "public_api_search_max_requests_per_window",
        1,
    )
    monkeypatch.setattr(
        api_module,
        "search_movies_hybrid",
        lambda query, limit: [],
    )
    headers = {"x-forwarded-for": "203.0.113.42"}

    first_response = client.get(
        "/api/search",
        params={"q": "The Matrix"},
        headers=headers,
    )
    second_response = client.get(
        "/api/search",
        params={"q": "The Matrix"},
        headers=headers,
    )

    api_rate_limiter.clear()

    assert first_response.status_code == 200
    assert first_response.headers["x-ratelimit-remaining"] == "0"
    assert second_response.status_code == 429
    assert second_response.headers["retry-after"] == "60"