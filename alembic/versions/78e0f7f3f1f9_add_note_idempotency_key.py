"""add note idempotency key

Revision ID: 78e0f7f3f1f9
Revises: afeae8cfbbce
Create Date: 2026-05-27 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "78e0f7f3f1f9"
down_revision: Union[str, Sequence[str], None] = "afeae8cfbbce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "notes",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_notes_user_id_idempotency_key",
        "notes",
        ["user_id", "idempotency_key"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_notes_user_id_idempotency_key",
        "notes",
        type_="unique",
    )
    op.drop_column("notes", "idempotency_key")
