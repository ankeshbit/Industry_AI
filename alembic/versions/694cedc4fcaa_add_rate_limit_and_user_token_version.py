"""add_rate_limit_and_user_token_version

Revision ID: 694cedc4fcaa
Revises: 947ed7ed0972
Create Date: 2026-11-25 22:05:52.238341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '694cedc4fcaa'
down_revision: Union[str, Sequence[str], None] = '947ed7ed0972'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema idempotently to support both fresh installations and existing databases."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Ensure rate_limit_attempts table exists
    if 'rate_limit_attempts' not in tables:
        op.create_table(
            'rate_limit_attempts',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('organisation_id', sa.String(length=36), nullable=True),
            sa.Column('key', sa.String(length=255), nullable=False),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_rate_limit_attempts_action'), 'rate_limit_attempts', ['action'], unique=False)
        op.create_index(op.f('ix_rate_limit_attempts_created_at'), 'rate_limit_attempts', ['created_at'], unique=False)
        op.create_index(op.f('ix_rate_limit_attempts_key'), 'rate_limit_attempts', ['key'], unique=False)
        op.create_index(op.f('ix_rate_limit_attempts_organisation_id'), 'rate_limit_attempts', ['organisation_id'], unique=False)
    else:
        columns = [c['name'] for c in inspector.get_columns('rate_limit_attempts')]
        if 'organisation_id' not in columns:
            op.add_column('rate_limit_attempts', sa.Column('organisation_id', sa.String(length=36), nullable=True))
            op.create_index(op.f('ix_rate_limit_attempts_organisation_id'), 'rate_limit_attempts', ['organisation_id'], unique=False)

    # 2. Ensure users.token_version exists
    if 'users' in tables:
        user_columns = [c['name'] for c in inspector.get_columns('users')]
        if 'token_version' not in user_columns:
            op.add_column('users', sa.Column('token_version', sa.Integer(), server_default='1', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'rate_limit_attempts' in tables:
        op.drop_table('rate_limit_attempts')
    if 'users' in tables:
        user_columns = [c['name'] for c in inspector.get_columns('users')]
        if 'token_version' in user_columns:
            op.drop_column('users', 'token_version')
