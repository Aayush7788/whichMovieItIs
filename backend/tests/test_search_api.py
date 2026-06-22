from fastapi.testclient import TestClient

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