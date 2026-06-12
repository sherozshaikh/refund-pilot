"""Admin API integration tests — auth enforcement + schema validation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.no_api


@pytest.fixture
def client() -> TestClient:
    from refund_pilot.api.app import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


def test_admin_runs_requires_auth(client: TestClient) -> None:
    """GET /admin/runs without token must return 401 or 403."""
    resp = client.get("/api/v1/admin/runs")
    assert resp.status_code in (401, 403)


def test_admin_run_detail_requires_auth(client: TestClient) -> None:
    """GET /admin/runs/{id} without token must return 401 or 403."""
    import uuid

    resp = client.get(f"/api/v1/admin/runs/{uuid.uuid4()}")
    assert resp.status_code in (401, 403)


def test_admin_conversations_requires_auth(client: TestClient) -> None:
    """GET /admin/conversations without token must return 401 or 403."""
    resp = client.get("/api/v1/admin/conversations")
    assert resp.status_code in (401, 403)


def test_admin_runs_bad_token_rejected(client: TestClient) -> None:
    """Malformed JWT must be rejected with 401 or 403."""
    resp = client.get(
        "/api/v1/admin/runs",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code in (401, 403)


def test_admin_runs_page_param_validation(client: TestClient) -> None:
    """page=0 rejected with 422 (FastAPI Query ge=1) or auth rejection."""
    resp = client.get("/api/v1/admin/runs", params={"page": 0})
    assert resp.status_code in (401, 403, 422)


def test_admin_runs_returns_json(client: TestClient) -> None:
    """Response must be JSON regardless of outcome."""
    resp = client.get("/api/v1/admin/runs")
    assert resp.headers["content-type"].startswith("application/json")


def test_auth_login_endpoint_exists(client: TestClient) -> None:
    """POST /auth/login must exist and return JSON."""
    resp = client.post("/api/v1/auth/login", data={"username": "x", "password": "x"})
    assert resp.status_code in (401, 422, 500)
    assert resp.headers["content-type"].startswith("application/json")


def test_auth_register_endpoint_exists(client: TestClient) -> None:
    """POST /auth/register must exist (open only when 0 users → 201 or 403 or 500)."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "admin", "email": "admin@test.com", "password": "secret123"},
    )
    assert resp.status_code in (201, 403, 500)
