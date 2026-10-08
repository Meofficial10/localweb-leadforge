"""campaign_wizard_fields

Revision ID: a1b2c3d4e5f6
Revises: 9f28a1f2ab12
Create Date: 2026-10-08 10:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9f28a1f2ab12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("campaigns", schema=None) as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("channels", sa.JSON().with_variant(sqlite.JSON(), "sqlite"), nullable=True))
        batch_op.add_column(sa.Column("budget_cap", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("campaigns", schema=None) as batch_op:
        batch_op.drop_column("budget_cap")
        batch_op.drop_column("channels")
        batch_op.drop_column("description")