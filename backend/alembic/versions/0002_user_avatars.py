"""user avatars — profile pictures stored in Postgres.

Revision ID: 0002_user_avatars
Revises: 0001_initial
Create Date: 2026-09-19
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_user_avatars"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_avatars",
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("users", sa.Column("avatar_updated_at", sa.DateTime(timezone=True),
                                     nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_updated_at")
    op.drop_table("user_avatars")
