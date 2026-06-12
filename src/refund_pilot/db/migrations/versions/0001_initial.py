from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- enums ---
    customer_tier = postgresql.ENUM("standard", "premium", "vip", name="customer_tier")
    order_status = postgresql.ENUM(
        "pending", "shipped", "delivered", "returned", name="order_status"
    )
    conversation_status = postgresql.ENUM("open", "closed", name="conversation_status")
    message_role = postgresql.ENUM("user", "assistant", name="message_role")
    agent_decision = postgresql.ENUM(
        "approved", "denied", "escalated", "fallback", name="agent_decision"
    )
    admin_role = postgresql.ENUM("superadmin", "admin", "readonly", name="admin_role")

    for enum in (
        customer_tier,
        order_status,
        conversation_status,
        message_role,
        agent_decision,
        admin_role,
    ):
        enum.create(op.get_bind(), checkfirst=True)

    # --- customers ---
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("tier", postgresql.ENUM(name="customer_tier", create_type=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_customers_email"),
    )

    # --- orders ---
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("product_sku", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status", postgresql.ENUM(name="order_status", create_type=False), nullable=False
        ),
        sa.Column("is_final_sale", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("purchase_date", sa.Date, nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="conversation_status", create_type=False),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_conversations_customer_id", "conversations", ["customer_id"])

    # --- agent_runs ---
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", sa.String(255), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column(
            "order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=True
        ),
        sa.Column("input_message", sa.Text, nullable=False),
        sa.Column(
            "decision", postgresql.ENUM(name="agent_decision", create_type=False), nullable=False
        ),
        sa.Column("reasoning", sa.Text, nullable=False, server_default=""),
        sa.Column("policy_clauses_cited", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("trace_steps", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("langsmith_run_id", sa.String(255), nullable=True),
        sa.Column("injection_detected", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("task_id", name="uq_agent_runs_task_id"),
    )
    op.create_index("ix_agent_runs_task_id", "agent_runs", ["task_id"], unique=True)
    op.create_index("ix_agent_runs_request_id", "agent_runs", ["request_id"])
    op.create_index("ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"])

    # --- chat_messages ---
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column("role", postgresql.ENUM(name="message_role", create_type=False), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "agent_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])

    # --- escalations ---
    op.create_table(
        "escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # --- admin_users ---
    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", postgresql.ENUM(name="admin_role", create_type=False), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("username", name="uq_admin_users_username"),
        sa.UniqueConstraint("email", name="uq_admin_users_email"),
    )


def downgrade() -> None:
    op.drop_table("admin_users")
    op.drop_table("escalations")
    op.drop_table("chat_messages")
    op.drop_table("agent_runs")
    op.drop_table("conversations")
    op.drop_table("orders")
    op.drop_table("customers")

    for name in (
        "admin_role",
        "agent_decision",
        "message_role",
        "conversation_status",
        "order_status",
        "customer_tier",
    ):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
