"""add content_mode auto_illustrate context_depth to stories

Revision ID: 795905b88fe5
Revises: a1178161be24
Create Date: 2026-02-10 16:47:37.917974

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '795905b88fe5'
down_revision: Union[str, None] = 'a1178161be24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stories', sa.Column('content_mode', sa.String(length=20), server_default='unrestricted', nullable=False))
    op.add_column('stories', sa.Column('auto_illustrate', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('stories', sa.Column('context_depth', sa.Integer(), server_default='5', nullable=False))


def downgrade() -> None:
    op.drop_column('stories', 'context_depth')
    op.drop_column('stories', 'auto_illustrate')
    op.drop_column('stories', 'content_mode')
