from fastapi.testclient import TestClient
from backend.app import main as main_module
from backend.app.main import app


client = TestClient(app)


def test_search_rejects_blank_query():
    response = client.get(
        "/search",
        params={"q": "   "},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "query cannot be empty",
    }

def test_search_returns_poster_metadata(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
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
        "/search",
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
