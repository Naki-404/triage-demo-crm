"""Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27
Bilim Academy domain: courses, packages, contracts, enrollments, installments, payments.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("max_discount_pct", sa.Integer(), nullable=False, server_default="10"))
    with op.batch_alter_table("clients") as batch:
        batch.add_column(sa.Column("birth_date", sa.Date(), nullable=True))

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_kzt", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_courses_code", "courses", ["code"], unique=True)

    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("price_kzt", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_packages_code", "packages", ["code"], unique=True)

    op.create_table(
        "package_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("package_id", sa.Integer(), sa.ForeignKey("packages.id"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
        sa.UniqueConstraint("package_id", "course_id", name="uq_package_course"),
    )
    op.create_index("ix_package_items_package_id", "package_items", ["package_id"])
    op.create_index("ix_package_items_course_id", "package_items", ["course_id"])

    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.String(64), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "completed", "cancelled", name="contractstatus"),
            nullable=False,
        ),
        sa.Column("total_kzt", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("number", name="uq_contracts_number"),
    )
    op.create_index("ix_contracts_number", "contracts", ["number"])
    op.create_index("ix_contracts_client_id", "contracts", ["client_id"])

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=True),
        sa.Column("package_id", sa.Integer(), sa.ForeignKey("packages.id"), nullable=True),
        sa.Column("price_kzt", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("client_id", "course_id", name="uq_enrollment_client_course"),
    )
    op.create_index("ix_enrollments_client_id", "enrollments", ["client_id"])
    op.create_index("ix_enrollments_course_id", "enrollments", ["course_id"])
    op.create_index("ix_enrollments_contract_id", "enrollments", ["contract_id"])

    op.create_table(
        "installments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount_kzt", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("scheduled", "paid", "overdue", "cancelled", name="installmentstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_installments_contract_id", "installments", ["contract_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("amount_kzt", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "paid", "failed", "refunded", name="paymentstatus"),
            nullable=False,
        ),
        sa.Column("card_token", sa.String(64), nullable=True),
        sa.Column("card_last4", sa.String(4), nullable=True),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_payments_contract_id", "payments", ["contract_id"])
    op.create_index("ix_payments_external_id", "payments", ["external_id"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("installments")
    op.drop_table("enrollments")
    op.drop_table("contracts")
    op.drop_table("package_items")
    op.drop_table("packages")
    op.drop_table("courses")
    with op.batch_alter_table("clients") as batch:
        batch.drop_column("birth_date")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("max_discount_pct")
