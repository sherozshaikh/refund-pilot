"""Customer and order read endpoints."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.api.dependencies import get_db
from refund_pilot.db.models import Customer, Order

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


class CustomerOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    tier: str

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: uuid.UUID
    product_name: str
    product_sku: str
    amount: float
    status: str
    is_final_sale: bool
    purchase_date: date
    category: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CustomerOut])
async def list_customers(db: AsyncSession = Depends(get_db)) -> list[Customer]:
    """Return all customers for the CustomerSelector dropdown."""
    result = await db.execute(select(Customer).order_by(Customer.name))
    return list(result.scalars().all())


@router.get("/{customer_id}/orders", response_model=list[OrderOut])
async def list_customer_orders(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[Order]:
    """Return orders for customer — populates OrderSelector dropdown."""
    result = await db.execute(
        select(Order).where(Order.customer_id == customer_id).order_by(Order.purchase_date.desc())
    )
    orders = list(result.scalars().all())
    if not orders:
        # Return empty list (not 404) — frontend shows "No orders found"
        return []
    return orders
