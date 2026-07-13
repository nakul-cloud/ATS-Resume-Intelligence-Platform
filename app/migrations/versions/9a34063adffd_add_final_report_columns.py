"""Add final report columns

Revision ID: 9a34063adffd
Revises: b50f6641afb1
Create Date: 2026-07-13 15:57:31.820201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9a34063adffd'
down_revision: Union[str, None] = 'b50f6641afb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interview_sessions', sa.Column('average_score', sa.Float(), nullable=True))
    op.add_column('interview_sessions', sa.Column('confidence_feedback', sa.Text(), nullable=True))
    op.add_column('interview_sessions', sa.Column('suggestions', sa.Text(), nullable=True))
    op.add_column('interview_sessions', sa.Column('strengths', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('interview_sessions', 'strengths')
    op.drop_column('interview_sessions', 'suggestions')
    op.drop_column('interview_sessions', 'confidence_feedback')
    op.drop_column('interview_sessions', 'average_score')
