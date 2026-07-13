"""add_work_experience_and_rewrite_cache

Revision ID: b50f6641afb1
Revises: 7a5d9976dec4
Create Date: 2026-07-13 11:49:06.756055

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b50f6641afb1'
down_revision: Union[str, None] = '7a5d9976dec4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column to candidates_parsed
    op.add_column('candidates_parsed', sa.Column('work_experience_json', sa.Text(), nullable=True))
    
    # 2. Create rewrite_cache table
    op.create_table(
        'rewrite_cache',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('candidate_hash', sa.String(length=64), nullable=False),
        sa.Column('jd_hash', sa.String(length=64), nullable=False),
        sa.Column('focus_areas_hash', sa.String(length=64), nullable=False),
        sa.Column('optimized_result_json', sa.Text(), nullable=False),
        sa.Column('raw_jd_text', sa.Text(), nullable=True),
        sa.Column('raw_candidate_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_rewrite_cache_candidate_hash', 'rewrite_cache', ['candidate_hash'], unique=False)
    op.create_index('ix_rewrite_cache_jd_hash', 'rewrite_cache', ['jd_hash'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_rewrite_cache_jd_hash', table_name='rewrite_cache')
    op.drop_index('ix_rewrite_cache_candidate_hash', table_name='rewrite_cache')
    op.drop_table('rewrite_cache')
    op.drop_column('candidates_parsed', 'work_experience_json')
