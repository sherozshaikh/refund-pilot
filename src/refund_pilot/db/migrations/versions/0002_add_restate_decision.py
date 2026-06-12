from __future__ import annotations

from alembic import op

revision = "0002_add_restate_decision"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE agent_decision ADD VALUE IF NOT EXISTS 'restate'")


def downgrade() -> None:
    # Postgres does not support removing enum values; downgrade is a no-op.
    pass
