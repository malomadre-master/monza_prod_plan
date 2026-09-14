from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_plan_versions"
down_revision: Union[str, None] = "0007_schedule_pins"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plan_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reason", sa.String(length=20), nullable=False),
        sa.Column("change_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("slots_json", sa.JSON(), nullable=False),
        sa.Column("changes_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_plan_versions_created_at", "plan_versions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_plan_versions_created_at", table_name="plan_versions")
    op.drop_table("plan_versions")
