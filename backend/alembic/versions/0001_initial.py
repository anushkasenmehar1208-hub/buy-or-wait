"""Initial schema — users, profiles, income, expenses, commitments, pending, requests, decisions.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "financial_profiles",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.String(32),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True,
                  index=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("current_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("minimum_safe_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("allows_partial_payment", sa.Boolean(), nullable=False),
        sa.Column("max_installment_months", sa.Integer(), nullable=True),
        sa.Column("payment_methods", sa.JSON(), nullable=False),
        sa.Column("stoppable_categories", sa.JSON(), nullable=False),
        sa.Column("reducible_categories", sa.JSON(), nullable=False),
    )
    op.create_table(
        "income_sources",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("profile_id", sa.String(32),
                  sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"), nullable=False,
                  index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("next_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "recurring_expenses",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("profile_id", sa.String(32),
                  sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"), nullable=False,
                  index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("next_date", sa.Date(), nullable=False),
        sa.Column("minimum_allowed_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("essential", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "financial_commitments",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("profile_id", sa.String(32),
                  sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"), nullable=False,
                  index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("is_installment", sa.Boolean(), nullable=False),
        sa.Column("installment_total", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "pending_payments",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("profile_id", sa.String(32),
                  sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"), nullable=False,
                  index=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "purchase_requests",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("profile_id", sa.String(32),
                  sa.ForeignKey("financial_profiles.id", ondelete="CASCADE"), nullable=False,
                  index=True),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "affordability_decisions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("request_id", sa.String(32),
                  sa.ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False,
                  unique=True),
        sa.Column("user_id", sa.String(32),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("affordability_status", sa.String(40), nullable=False),
        sa.Column("amount_safe_to_pay", sa.Numeric(18, 2), nullable=False),
        sa.Column("recommended_payment_method", sa.String(40), nullable=False),
        sa.Column("payment_plan", sa.Text(), nullable=True),
        sa.Column("earliest_date_for_full_payment", sa.Date(), nullable=True),
        sa.Column("spending_changes_needed", sa.Text(), nullable=True),
        sa.Column("decision_explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "affordability_decisions", "purchase_requests", "pending_payments",
        "financial_commitments", "recurring_expenses", "income_sources",
        "financial_profiles", "users",
    ):
        op.drop_table(table)
