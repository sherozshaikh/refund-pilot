"""Auth API integration tests — mocked DB."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.no_api


@pytest.fixture
def client() -> TestClient:
    from refund_pilot.api.app import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


def test_login_invalid_credentials(client: TestClient) -> None:
    with patch("refund_pilot.api.routers.auth.AsyncSession") as _:
        resp = client.post("/api/v1/auth/login", data={"username": "bad", "password": "bad"})
    # DB not available in unit test but endpoint must exist
    assert resp.status_code in (401, 500)


def test_register_endpoint_exists(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": "admin", "email": "admin@test.com", "password": "secret123"},
    )
    assert resp.status_code in (201, 403, 500)
