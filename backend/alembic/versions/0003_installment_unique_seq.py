"""Revision ID: 0003
Revises: 0002
Create Date: 2026-10-09
One installment row per (contract, seq): a repeated schedule request must not duplicate the plan.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("installments") as batch:
        batch.create_unique_constraint("uq_installment_contract_seq", ["contract_id", "seq"])


def downgrade() -> None:
    with op.batch_alter_table("installments") as batch:
        batch.drop_constraint("uq_installment_contract_seq", type_="unique")
