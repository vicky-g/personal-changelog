"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entries_date", "entries", ["date"])
    op.create_index("ix_entries_created_at", "entries", ["created_at"])

    # PostgreSQL enum types are created implicitly when the table is created,
    # but we name them explicitly so downgrade can drop them cleanly.
    period_type = sa.Enum(
        "weekly", "monthly", "quarterly",
        name="periodtype",
    )
    summary_type = sa.Enum(
        "reflection", "perf_review", "opportunities",
        name="summarytype",
    )

    op.create_table(
        "summaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("period_type", period_type, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("raw_bullets", sa.JSON(), nullable=False),
        sa.Column("generated_text", sa.Text(), nullable=True),
        sa.Column("summary_type", summary_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_summaries_created_at", "summaries", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_summaries_created_at", table_name="summaries")
    op.drop_table("summaries")
    op.drop_index("ix_entries_created_at", table_name="entries")
    op.drop_index("ix_entries_date", table_name="entries")
    op.drop_table("entries")

    # Drop enum types explicitly — dropping the table does not drop them.
    op.execute("DROP TYPE IF EXISTS summarytype")
    op.execute("DROP TYPE IF EXISTS periodtype")
