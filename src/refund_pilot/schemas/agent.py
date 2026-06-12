from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AgentDecision(BaseModel):
    decision: Literal["approved", "denied", "escalated", "fallback"]
    policy_clauses_cited: list[str] = []
    reasoning: str = ""
    customer_facing_message: str = (
        "We're unable to process your request right now. Please try again."
    )
    confidence: float = 1.0
    injection_detected: bool = False


class TraceStep(BaseModel):
    node: str
    input: dict[str, object]
    output: dict[str, object]
    duration_ms: int
