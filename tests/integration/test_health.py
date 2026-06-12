"""Health endpoint smoke tests — no DB required."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.no_api


@pytest.fixture
def client() -> TestClient:
    from refund_pilot.api.app import create_app

    return TestClient(create_app(), raise_server_exceptions=True)


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
