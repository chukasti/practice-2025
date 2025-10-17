"""init_new

Revision ID: f75b8809764c
Revises:
Create Date: 2025-10-17 21:54:21.753883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f75b8809764c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE public.active_session (
            userid TEXT NOT NULL,
            token TEXT NOT NULL,
            expires_at TIMESTAMP
        );
    """)

    op.execute("""
        CREATE TABLE public.bruteforce_protect (
            user_id TEXT NOT NULL,
            last_attempt TIMESTAMPTZ,
            attempt_value NUMERIC
        );
    """)

    op.execute("""
        CREATE TABLE public.transactions (
            id TEXT NOT NULL,
            amount NUMERIC NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            account_id TEXT NOT NULL,
            merchant_id TEXT NOT NULL,
            status TEXT NOT NULL
        );
    """)

    op.execute("""
        CREATE TABLE public.users (
            user_id TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            name_surname TEXT NOT NULL,
            balance NUMERIC(12,2) NOT NULL,
            account_status TEXT NOT NULL
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS public.users;")
    op.execute("DROP TABLE IF EXISTS public.transactions;")
    op.execute("DROP TABLE IF EXISTS public.bruteforce_protect;")
    op.execute("DROP TABLE IF EXISTS public.active_session;")
