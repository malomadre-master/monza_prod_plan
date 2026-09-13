from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_schedule_pins"
down_revision: Union[str, None] = "0006_work_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedule_pins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("center_code", sa.String(length=40), nullable=False),
        sa.Column("start", sa.Date(), nullable=False),
        sa.Column("finish", sa.Date(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("item_id", "center_code", name="uq_schedule_pin_item_center"),
    )
    op.create_index("ix_schedule_pins_item_id", "schedule_pins", ["item_id"])
    op.create_index("ix_schedule_pins_center_code", "schedule_pins", ["center_code"])


def downgrade() -> None:
    op.drop_index("ix_schedule_pins_center_code", table_name="schedule_pins")
    op.drop_index("ix_schedule_pins_item_id", table_name="schedule_pins")
    op.drop_table("schedule_pins")
