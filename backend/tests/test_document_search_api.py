from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.main import app


client = TestClient(app)


def test_document_search_endpoint_returns_results(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "search_movies_document_hybrid",
        lambda query, limit: [
            {
                "movie_key": "cmu:603",
                "wikipedia_movie_id": "603",
                "title": "The Matrix",
                "release_date": "1999-03-31",
                "genres": ["Science Fiction"],
                "plot_summary": "A hacker discovers a simulated world.",
                "tmdb_id": 603,
                "poster_path": "/matrix.jpg",
                "poster_url": (
                    "https://image.tmdb.org/t/p/"
                    "w342/matrix.jpg"
                ),
                "metadata_source": "tmdb",
                "score": 0.5,
            }
        ],
    )

    response = client.get(
        "/search/documents",
        params={
            "q": "computer simulation hacker",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["query"] == "computer simulation hacker"
    assert response.json()["results"][0]["title"] == "The Matrix"

def test_hybrid_v2_search_endpoint_returns_results(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "search_movies_hybrid_v2",
        lambda query, limit: [
            {
                "movie_key": "cmu:13053911",
                "wikipedia_movie_id": "13053911",
                "title": "Friday the 13th",
                "release_date": "1980-05-09",
                "genres": ["Horror"],
                "plot_summary": "Camp counselors are stalked.",
                "tmdb_id": 4488,
                "poster_path": "/poster.jpg",
                "poster_url": (
                    "https://image.tmdb.org/t/p/"
                    "w342/poster.jpg"
                ),
                "metadata_source": "tmdb",
                "score": 0.5,
            }
        ],
    )

    response = client.get(
        "/search/hybrid-v2",
        params={
            "q": "hockey mask summer camp",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["title"] == "Friday the 13th"
