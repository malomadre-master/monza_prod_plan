from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_user_efficiency"
down_revision: Union[str, None] = "0003_docs_and_centers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("efficiency", sa.Numeric(4, 2), nullable=False, server_default="1.00"),
    )


def downgrade() -> None:
    op.drop_column("users", "efficiency")
