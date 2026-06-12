from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AdminRunSummary(BaseModel):
    id: str
    task_id: str
    customer_id: str
    decision: Literal["approved", "denied", "escalated", "fallback", "restate"]
    latency_ms: int
    input_tokens: int
    output_tokens: int
    created_at: datetime


class AdminRunDetail(AdminRunSummary):
    input_message: str
    reasoning: str
    policy_clauses_cited: list[str]
    trace_steps: list[dict[str, object]]
    injection_detected: bool
    langsmith_run_id: str | None


class AdminRunList(BaseModel):
    items: list[AdminRunSummary]
    total: int
    page: int
    limit: int
