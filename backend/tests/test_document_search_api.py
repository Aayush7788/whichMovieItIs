from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_experimental_search_routes_are_not_public():
    routes = (
        "/api/search/vector",
        "/api/search/hybrid",
        "/api/search/reranked",
        "/api/search/documents",
        "/api/search/hybrid-v2",
    )

    for route in routes:
        response = client.get(route, params={"q": "The Matrix"})
        assert response.status_code == 404