"""Admin endpoints: paginated run history + full trace detail."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.api.dependencies import get_db, require_admin
from refund_pilot.db.models import AgentRun, Conversation, Customer

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class RunSummary(BaseModel):
    id: uuid.UUID
    task_id: str
    customer_id: uuid.UUID
    customer_name: str
    input_message: str
    decision: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    injection_detected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RunDetail(RunSummary):
    input_message: str
    reasoning: str
    policy_clauses_cited: list[str]
    trace_steps: list[dict[str, object]]
    langsmith_run_id: str | None
    conversation_id: uuid.UUID


class RunList(BaseModel):
    items: list[RunSummary]
    total: int
    page: int
    limit: int


@router.get("/runs", response_model=RunList, dependencies=[Depends(require_admin)])
async def list_runs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    decision: str | None = Query(None),
    conversation_id: uuid.UUID | None = Query(None),
    customer_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> RunList:
    """Return paginated agent run history with optional filters."""
    query = select(AgentRun).order_by(AgentRun.created_at.desc())
    count_query = select(AgentRun)

    if decision:
        query = query.where(AgentRun.decision == decision)
        count_query = count_query.where(AgentRun.decision == decision)
    if conversation_id:
        query = query.where(AgentRun.conversation_id == conversation_id)
        count_query = count_query.where(AgentRun.conversation_id == conversation_id)
    if customer_id:
        query = query.where(AgentRun.customer_id == customer_id)
        count_query = count_query.where(AgentRun.customer_id == customer_id)

    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    runs = list(result.scalars().all())

    total_result = await db.execute(select(func.count()).select_from(count_query.subquery()))
    total = total_result.scalar_one()

    # Batch-fetch customer names — one IN query per page, not N queries
    customer_ids = list({r.customer_id for r in runs})
    cust_result = await db.execute(select(Customer).where(Customer.id.in_(customer_ids)))
    name_by_id = {c.id: c.name for c in cust_result.scalars().all()}

    items = [
        RunSummary(
            id=r.id,
            task_id=r.task_id,
            customer_id=r.customer_id,
            customer_name=name_by_id.get(r.customer_id, "Unknown"),
            input_message=r.input_message,
            decision=r.decision,
            latency_ms=r.latency_ms,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            injection_detected=r.injection_detected,
            created_at=r.created_at,
        )
        for r in runs
    ]
    return RunList(items=items, total=total, page=page, limit=limit)


@router.get("/runs/{run_id}", response_model=RunDetail, dependencies=[Depends(require_admin)])
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RunDetail:
    """Return full trace for a single agent run."""
    run = await db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    customer = await db.get(Customer, run.customer_id)
    return RunDetail(
        id=run.id,
        task_id=run.task_id,
        customer_id=run.customer_id,
        customer_name=customer.name if customer else "Unknown",
        decision=run.decision,
        latency_ms=run.latency_ms,
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
        injection_detected=run.injection_detected,
        created_at=run.created_at,
        input_message=run.input_message,
        reasoning=run.reasoning,
        policy_clauses_cited=run.policy_clauses_cited,
        trace_steps=run.trace_steps,
        langsmith_run_id=run.langsmith_run_id,
        conversation_id=run.conversation_id,
    )


@router.get(
    "/conversations", response_model=list[dict[str, object]], dependencies=[Depends(require_admin)]
)
async def list_conversations(
    conv_status: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    """Return conversations with summary, newest first."""
    query = select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
    if conv_status:
        query = query.where(Conversation.status == conv_status)
    result = await db.execute(query)
    convs = list(result.scalars().all())
    return [
        {
            "id": str(c.id),
            "customer_id": str(c.customer_id),
            "status": c.status,
            "created_at": str(c.created_at),
        }
        for c in convs
    ]
