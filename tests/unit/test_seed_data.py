"""Seed data integrity tests."""

from __future__ import annotations

import pytest

from refund_pilot.data.customers import CUSTOMERS
from refund_pilot.data.orders import ORDERS

pytestmark = pytest.mark.no_api


def test_exactly_15_customers() -> None:
    assert len(CUSTOMERS) == 15


def test_customer_ids_unique() -> None:
    ids = [c.id for c in CUSTOMERS]
    assert len(ids) == len(set(ids))


def test_customer_emails_unique() -> None:
    emails = [c.email for c in CUSTOMERS]
    assert len(emails) == len(set(emails))


def test_customer_tiers_valid() -> None:
    valid = {"standard", "premium", "vip"}
    for c in CUSTOMERS:
        assert c.tier in valid, f"{c.name} has invalid tier {c.tier}"


def test_orders_reference_valid_customers() -> None:
    customer_ids = {c.id for c in CUSTOMERS}
    for o in ORDERS:
        assert o.customer_id in customer_ids, (
            f"Order {o.id} references unknown customer {o.customer_id}"
        )


def test_order_amounts_positive() -> None:
    for o in ORDERS:
        assert o.amount > 0, f"Order {o.id} has non-positive amount {o.amount}"


def test_order_ids_unique() -> None:
    ids = [o.id for o in ORDERS]
    assert len(ids) == len(set(ids))


def test_all_customers_have_at_least_one_order() -> None:
    customer_ids_with_orders = {o.customer_id for o in ORDERS}
    for c in CUSTOMERS:
        assert c.id in customer_ids_with_orders, f"{c.name} has no orders"
