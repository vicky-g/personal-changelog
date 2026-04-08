"""add entry_type column to entries

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-08
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    entry_type = sa.Enum("glow", "grow", name="entrytype")
    entry_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "entries",
        sa.Column(
            "entry_type",
            sa.Enum("glow", "grow", name="entrytype"),
            nullable=False,
            server_default="glow",
        ),
    )
    # Remove the server default once backfill is done — the application sets it explicitly.
    op.alter_column("entries", "entry_type", server_default=None)


def downgrade() -> None:
    op.drop_column("entries", "entry_type")
    op.execute("DROP TYPE IF EXISTS entrytype")
