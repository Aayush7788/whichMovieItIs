from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.main import app


client = TestClient(app)


def catalog_movie():
    return {
        "movie_key": "cmu:30007",
        "wikipedia_movie_id": "30007",
        "title": "The Matrix",
        "release_date": "1999-03-31",
        "genres": ["Science Fiction"],
        "plot_summary": "A hacker discovers a simulated world.",
        "tmdb_id": 603,
        "poster_path": "/matrix.jpg",
        "poster_url": "https://image.tmdb.org/t/p/w342/matrix.jpg",
        "metadata_source": "tmdb",
        "source": "cmu_movie_summary_corpus",
    }


def test_movies_endpoint_returns_catalog(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "list_movies",
        lambda limit, offset: {
            "results": [catalog_movie()],
            "total": 1,
            "limit": limit,
            "offset": offset,
        },
    )

    response = client.get(
        "/api/movies",
        params={
            "limit": 12,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["limit"] == 12
    assert payload["results"][0]["movie_key"] == "cmu:30007"
    assert payload["results"][0]["poster_url"].endswith(
        "/w342/matrix.jpg"
    )


def test_movie_detail_endpoint_returns_database_fields(monkeypatch):
    detail = {
        **catalog_movie(),
        "freebase_movie_id": "/m/0f4vbz",
        "box_office_revenue": 463517383.0,
        "runtime": 136.0,
        "languages": ["English Language"],
        "countries": ["United States of America"],
        "search_boost_text": "Neo Morpheus Trinity",
    }

    monkeypatch.setattr(
        main_module,
        "get_movie_detail",
        lambda movie_key: detail if movie_key == "cmu:30007" else None,
    )

    response = client.get("/api/movies/cmu:30007")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "The Matrix"
    assert payload["runtime"] == 136.0
    assert payload["languages"] == ["English Language"]


def test_movie_detail_endpoint_returns_404(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "get_movie_detail",
        lambda movie_key: None,
    )

    response = client.get("/api/movies/cmu:missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "movie not found"}
