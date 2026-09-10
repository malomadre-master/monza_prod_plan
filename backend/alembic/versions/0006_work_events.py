from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_work_events"
down_revision: Union[str, None] = "0005_calendar_attendance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("center_code", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.Enum("taken", "done", "materials_confirmed", name="work_event_kind"), nullable=False),
        sa.Column("volume", sa.Numeric(10, 2), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("item_id", "center_code", "kind", name="uq_work_event_item_center_kind"),
    )
    op.create_index("ix_work_events_item_id", "work_events", ["item_id"])
    op.create_index("ix_work_events_center_code", "work_events", ["center_code"])


def downgrade() -> None:
    op.drop_index("ix_work_events_center_code", table_name="work_events")
    op.drop_index("ix_work_events_item_id", table_name="work_events")
    op.drop_table("work_events")
    sa.Enum(name="work_event_kind").drop(op.get_bind(), checkfirst=True)
