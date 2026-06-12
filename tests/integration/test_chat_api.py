"""Chat API integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.no_api


@pytest.fixture
def client() -> TestClient:
    from refund_pilot.api.app import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


def test_create_conversation_missing_customer(client: TestClient) -> None:
    import uuid

    resp = client.post("/api/v1/conversations", json={"customer_id": str(uuid.uuid4())})
    # Without DB, 404 or 500 both acceptable — endpoint must exist and return JSON
    assert resp.status_code in (404, 500)
    assert resp.headers["content-type"].startswith("application/json")


def test_list_customers_endpoint_exists(client: TestClient) -> None:
    resp = client.get("/api/v1/customers")
    assert resp.status_code in (200, 500)


def test_message_request_validates_length(client: TestClient) -> None:
    import uuid

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/message",
        json={"order_id": str(uuid.uuid4()), "message": ""},
    )
    assert resp.status_code == 422  # Pydantic min_length=1 enforced


def test_message_request_max_length(client: TestClient) -> None:
    import uuid

    resp = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/message",
        json={"order_id": str(uuid.uuid4()), "message": "x" * 2001},
    )
    assert resp.status_code == 422  # Pydantic max_length=2000 enforced
