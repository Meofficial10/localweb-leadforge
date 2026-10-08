"""performance_indexes

Revision ID: c52d1e9a0b11
Revises: a1b2c3d4e5f6
Create Date: 2026-10-08 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c52d1e9a0b11"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # M5: indexes for the hot list/queue queries — leads by campaign,
    # messages by lead and by status, audit log by created_at.
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_leads_campaign_id"), ["campaign_id"], unique=False)
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_messages_lead_id"), ["lead_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_messages_status"), ["status"], unique=False)
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_audit_log_created_at"), ["created_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("audit_log", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_audit_log_created_at"))
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_messages_status"))
        batch_op.drop_index(batch_op.f("ix_messages_lead_id"))
    with op.batch_alter_table("leads", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_leads_campaign_id"))
