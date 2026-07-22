from fastapi.testclient import TestClient
from backend.app import api as api_module
from backend.app.main import app


client = TestClient(app)


def test_search_health_reports_model_status(monkeypatch):
    monkeypatch.setattr(
        api_module,
        "is_embedding_model_ready",
        lambda: False,
    )

    response = client.get("/api/health/search")

    assert response.status_code == 200
    assert response.json() == {"status": "warming"}


def test_search_rejects_blank_query():
    response = client.get(
        "/api/search",
        params={"q": "   "},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "query cannot be empty",
    }

def test_search_rejects_query_over_character_limit():
    response = client.get(
        "/api/search",
        params={"q": "x" * 1001},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "query cannot exceed 1000 characters",
    }


def test_search_returns_poster_metadata(
    monkeypatch,
):
    monkeypatch.setattr(
        api_module,
        "search_movies_hybrid",
        lambda query, limit: [
            {
                "movie_key": "cmu:30007",
                "wikipedia_movie_id": "30007",
                "title": "The Matrix",
                "release_date": "1999-03-31",
                "genres": ["Science Fiction"],
                "plot_summary": "A hacker discovers the truth.",
                "tmdb_id": 603,
                "poster_path": "/poster.jpg",
                "poster_url": (
                    "https://image.tmdb.org/t/p/"
                    "w342/poster.jpg"
                ),
                "metadata_source": "tmdb",
                "score": 0.1,
            }
        ],
    )

    response = client.get(
        "/api/search",
        params={
            "q": "reality simulation",
            "limit": 5,
        },
    )

    assert response.status_code == 200

    movie = response.json()["results"][0]

    assert movie["title"] == "The Matrix"
    assert movie["tmdb_id"] == 603
    assert movie["poster_url"].endswith(
        "/w342/poster.jpg"
    )

def test_unprefixed_search_route_is_not_exposed():
    response = client.get(
        "/search",
        params={"q": "The Matrix"},
    )

    assert response.status_code == 404
