"""apify_and_lead_sources

Revision ID: 9f28a1f2ab12
Revises: 3cbd6607908a
Create Date: 2026-10-07 12:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

from app.models.base import GUID

revision: str = '9f28a1f2ab12'
down_revision: Union[str, None] = '3cbd6607908a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add lead_sources (multi-select JSON) + index on jobs queues used often
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.add_column(sa.Column('lead_sources', sa.JSON().with_variant(sqlite.JSON(), 'sqlite'), nullable=True))
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_jobs_stage'), ['stage'], unique=False)
        batch_op.create_index(batch_op.f('ix_jobs_status'), ['status'], unique=False)

    # apify_runs table to track actor run status/cost for the run view
    op.create_table('apify_runs',
    sa.Column('id', GUID(length=36), nullable=False),
    sa.Column('campaign_id', GUID(length=36), nullable=True),
    sa.Column('apify_run_id', sa.String(length=128), nullable=True),
    sa.Column('actor_id', sa.String(length=128), nullable=False),
    sa.Column('search', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('items_fetched', sa.Integer(), nullable=False),
    sa.Column('leads_imported', sa.Integer(), nullable=False),
    sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('apify_runs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_apify_runs_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_apify_runs_created_at'), ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('apify_runs')
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_jobs_stage'))
        batch_op.drop_index(batch_op.f('ix_jobs_status'))
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        batch_op.drop_column('lead_sources')
