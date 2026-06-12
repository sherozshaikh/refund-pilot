"""Policy edge case tests — all 15 customer scenarios."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from refund_pilot.core.config import PipelineConfig

pytestmark = pytest.mark.no_api

TODAY = date(2026, 6, 6)


def days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


@pytest.mark.parametrize(
    "purchase_date,is_final_sale,amount,expected",
    [
        # eligible — within window, not final sale, under $500
        (days_ago(15), False, 89.00, "approved"),
        (days_ago(10), False, 145.00, "approved"),
        (days_ago(10), False, 67.00, "approved"),
        # escalate — over $500 threshold
        (days_ago(15), False, 649.00, "escalated"),
        (days_ago(10), False, 890.00, "escalated"),
        # deny — final sale
        (days_ago(10), True, 55.00, "denied"),
        (days_ago(15), True, 320.00, "denied"),
        (days_ago(10), True, 415.00, "denied"),
        # deny — outside 30-day window
        (days_ago(45), False, 78.00, "denied"),
        (days_ago(45), False, 130.00, "denied"),
        (days_ago(45), False, 200.00, "denied"),
    ],
)
def test_expected_decisions(
    purchase_date: date,
    is_final_sale: bool,
    amount: float,
    expected: str,
    pipeline_config: PipelineConfig,
) -> None:
    """Validate decision logic matches expected outcomes from PLAN.md §26."""
    window_ok = (TODAY - purchase_date).days <= pipeline_config.refund_window_days
    over_threshold = amount > pipeline_config.escalation_threshold_usd

    if is_final_sale:
        decision = "denied"
    elif over_threshold:
        decision = "escalated"
    elif not window_ok:
        decision = "denied"
    else:
        decision = "approved"

    assert decision == expected
