"""add_projects_accomplishments_hobbies

Revision ID: 7a5d9976dec4
Revises: 21b5dbf7e53a
Create Date: 2026-07-11 13:09:16.980233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7a5d9976dec4'
down_revision: Union[str, None] = '21b5dbf7e53a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('candidates_parsed', sa.Column('projects_json', sa.Text(), nullable=True))
    op.add_column('candidates_parsed', sa.Column('accomplishments_json', sa.Text(), nullable=True))
    op.add_column('candidates_parsed', sa.Column('hobbies_json', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('candidates_parsed', 'hobbies_json')
    op.drop_column('candidates_parsed', 'accomplishments_json')
    op.drop_column('candidates_parsed', 'projects_json')
