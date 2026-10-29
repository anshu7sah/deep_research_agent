import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def fake_api_key():
    with patch.dict(os.environ, {"DR_OPENAI_API_KEY": "sk-test-key"}):
        yield


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_start_research_invalid_mode(client):
    with patch("api.routes.research.get_llm_client") as mock_get:
        mock_get.return_value = MagicMock()
        response = client.post(
            "/api/research",
            json={"query": "test query", "mode": "invalid"},
        )
    assert response.status_code == 400


def test_start_research_creates_session(client):
    with patch("api.routes.research.get_llm_client") as mock_get_llm, \
         patch("api.routes.research.get_orchestrator") as mock_orch:
        mock_get_llm.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.run = AsyncMock()
        mock_instance.emit = AsyncMock()
        mock_orch.return_value = mock_instance

        response = client.post(
            "/api/research",
            json={"query": "What is AI?", "mode": "code"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert len(data["session_id"]) == 12


def test_get_nonexistent_session(client):
    response = client.get("/api/research/nonexistent")
    assert response.status_code == 404


def test_clarify_nonexistent_session(client):
    response = client.post(
        "/api/research/nonexistent/clarify",
        json={"answers": {}},
    )
    assert response.status_code == 404


def test_download_md_no_report(client):
    response = client.get("/api/research/nonexistent/report/md")
    assert response.status_code == 404


def test_download_pdf_no_report(client):
    response = client.get("/api/research/nonexistent/report/pdf")
    assert response.status_code == 404
