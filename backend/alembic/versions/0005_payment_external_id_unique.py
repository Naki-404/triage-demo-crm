"""Revision ID: 0005
Revises: 0004
Create Date: 2026-10-17
One payment per gateway id: a webhook delivered twice at the same time must not create two payments.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # keep the first payment of any duplicated gateway id before the constraint goes on
    op.execute(sa.text(
        "DELETE FROM payments WHERE external_id IS NOT NULL AND id NOT IN "
        "(SELECT MIN(id) FROM payments WHERE external_id IS NOT NULL GROUP BY external_id)"
    ))
    op.drop_index("ix_payments_external_id", table_name="payments")
    op.create_index("ix_payments_external_id", "payments", ["external_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_payments_external_id", table_name="payments")
    op.create_index("ix_payments_external_id", "payments", ["external_id"])
