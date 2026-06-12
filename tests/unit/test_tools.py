"""Tool function tests — check_policy pure function (no DB needed)."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from refund_pilot.agent.tools import check_policy
from refund_pilot.core.config import PipelineConfig

pytestmark = pytest.mark.no_api

TODAY = date(2026, 6, 6)


def make_order(
    *,
    amount: float = 89.0,
    is_final_sale: bool = False,
    days_ago: int = 15,
    status: str = "delivered",
) -> MagicMock:
    order = MagicMock()
    order.amount = amount
    order.is_final_sale = is_final_sale
    order.purchase_date = TODAY - timedelta(days=days_ago)
    order.status = status
    return order


@pytest.fixture
def config() -> PipelineConfig:
    return PipelineConfig()


def test_eligible_order(config: PipelineConfig) -> None:
    order = make_order(amount=89.0, days_ago=15)
    verdict = check_policy(order, config, today=TODAY)
    assert verdict.decision == "approved"
    assert verdict.eligible is True


def test_final_sale_denied(config: PipelineConfig) -> None:
    order = make_order(is_final_sale=True, amount=55.0, days_ago=10)
    verdict = check_policy(order, config, today=TODAY)
    assert verdict.decision == "denied"
    assert any("Section 2" in c for c in verdict.clauses)


def test_outside_window_denied(config: PipelineConfig) -> None:
    order = make_order(days_ago=45)
    verdict = check_policy(order, config, today=TODAY)
    assert verdict.decision == "denied"
    assert any("Section 1" in c for c in verdict.clauses)


def test_high_value_escalated(config: PipelineConfig) -> None:
    order = make_order(amount=649.0, days_ago=15)
    verdict = check_policy(order, config, today=TODAY)
    assert verdict.decision == "escalated"
    assert any("Section 3" in c for c in verdict.clauses)


def test_fraud_indicator_escalated(config: PipelineConfig) -> None:
    order = make_order(amount=100.0, days_ago=10)
    verdict = check_policy(order, config, recent_refunds=3, today=TODAY)
    assert verdict.decision == "escalated"
    assert any("Section 5" in c for c in verdict.clauses)


def test_final_sale_beats_defective(config: PipelineConfig) -> None:
    """Final sale denial takes precedence over defective claim."""
    order = make_order(is_final_sale=True, amount=320.0, days_ago=15)
    verdict = check_policy(order, config, today=TODAY)
    assert verdict.decision == "denied"


def test_window_boundary_exact_30_days(config: PipelineConfig) -> None:
    order = make_order(days_ago=30)
    verdict = check_policy(order, config, today=TODAY)
    assert verdict.decision == "approved"


def test_window_boundary_31_days(config: PipelineConfig) -> None:
    order = make_order(days_ago=31)
    verdict = check_policy(order, config, today=TODAY)
    assert verdict.decision == "denied"
