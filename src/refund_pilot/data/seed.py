"""Idempotent seed CLI: uv run python -m refund_pilot.data.seed"""

from __future__ import annotations

import asyncio
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from refund_pilot.core.config import Settings
from refund_pilot.core.logging import configure_logging
from refund_pilot.core.security import hash_password
from refund_pilot.data.customers import CUSTOMERS
from refund_pilot.data.orders import ORDERS
from refund_pilot.db.models import AdminUser, Customer, Order
from refund_pilot.db.session import AsyncSessionLocal


async def seed_customers(db: AsyncSession) -> None:
    """Insert customers that don't already exist."""
    for c in CUSTOMERS:
        existing = await db.get(Customer, uuid.UUID(c.id))
        if existing:
            continue
        db.add(
            Customer(
                id=uuid.UUID(c.id),
                name=c.name,
                email=c.email,
                phone=c.phone,
                tier=c.tier,
            )
        )
        logger.info("seeded_customer", name=c.name, id=c.id)
    await db.commit()


async def seed_orders(db: AsyncSession) -> None:
    """Insert orders that don't already exist."""
    for o in ORDERS:
        existing = await db.get(Order, uuid.UUID(o.id))
        if existing:
            continue
        db.add(
            Order(
                id=uuid.UUID(o.id),
                customer_id=uuid.UUID(o.customer_id),
                product_name=o.product_name,
                product_sku=o.product_sku,
                amount=o.amount,
                status=o.status,
                is_final_sale=o.is_final_sale,
                purchase_date=o.purchase_date,
                category=o.category,
            )
        )
        logger.info("seeded_order", product=o.product_name, id=o.id)
    await db.commit()


async def seed_admin(db: AsyncSession) -> None:
    """Create superadmin from env vars if no admin users exist."""
    existing = await db.execute(select(AdminUser).limit(1))
    if existing.scalar_one_or_none() is not None:
        return
    settings = Settings()
    db.add(
        AdminUser(
            id=uuid.uuid4(),
            username=settings.admin_username,
            email=f"{settings.admin_username}@refund-pilot.local",
            hashed_password=hash_password(settings.admin_password),
            role="superadmin",
            is_active=True,
        )
    )
    await db.commit()
    logger.info("seeded_admin", username=settings.admin_username)


async def run() -> None:
    configure_logging()
    logger.info("seed_start")
    async with AsyncSessionLocal() as db:
        await seed_customers(db)
        await seed_orders(db)
        await seed_admin(db)
    logger.info("seed_complete", customers=len(CUSTOMERS), orders=len(ORDERS))


if __name__ == "__main__":
    asyncio.run(run())
