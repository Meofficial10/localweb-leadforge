"""pipeline_no_contact_reason

Revision ID: d1e2f3a4b5c6
Revises: c52d1e9a0b11
Create Date: 2026-10-15 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c52d1e9a0b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Workstream D: persist why a lead was marked no_contact and which public
    # sources enrichment tried. Nullable so existing rows are unaffected.
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.add_column(sa.Column("no_contact_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("enrichment_sources", sa.JSON().with_variant(sqlite.JSON(), "sqlite"), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.drop_column("enrichment_sources")
        batch_op.drop_column("no_contact_reason")