"""init

Revision ID: 0a2c7799e43c
Revises:
Create Date: 2025-10-17 21:45:26.430912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a2c7799e43c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
            CREATE TABLE public.active_session (
                userid TEXT NOT NULL,
                token TEXT NOT NULL,
                express_at TIMESTAMP NOT NULL
            );
        """)

    op.execute("""
            CREATE TABLE public.audit_logs (    
                id SERIAL4 NOT NULL,
                transaction_id TEXT NOT NULL,
                amount NUMERIC(15, 2) NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                account_id TEXT NOT NULL,
                merchant_id TEXT NOT NULL,
                status TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                raw_payload JSONB NOT NULL
            );
        """)

    op.execute("""
            CREATE TABLE public.bruteforce_protect (
                user_id TEXT NOT NULL,
                last_atempt TIMESTAMPTZ NOT NULL,
                attempt_value NUMERIC NOT NULL
            );
        """)

    op.execute("""
            CREATE TABLE public.users (
                user_id TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                name_surname TEXT NOT NULL,
                account_status TEXT NOT NULL
            );
        """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS public.users;")
    op.execute("DROP TABLE IF EXISTS public.audit_logs;")
    op.execute("DROP TABLE IF EXISTS public.bruteforce_protect;")
    op.execute("DROP TABLE IF EXISTS public.active_session;")
