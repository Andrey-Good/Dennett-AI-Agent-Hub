from fastapi.testclient import TestClient
from apps.ai_core.ai_core.main import app  # Still imports from main.py

client = TestClient(app)


def test_hub_search():
    response = client.get("/hub/search?query=gpt")
    assert response.status_code in [200, 401]  # Depending on auth


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
