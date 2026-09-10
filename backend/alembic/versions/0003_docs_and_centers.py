from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_docs_and_centers"
down_revision: Union[str, None] = "0002_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'in_design'")
        op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'in_production'")

    op.add_column("order_items", sa.Column("procurement_needed", sa.Boolean(), nullable=True))
    op.add_column("order_items", sa.Column("construction_done_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("store", sa.Enum("production", "procurement", name="attachment_store"), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_attachments_item_id", "attachments", ["item_id"])

    op.create_table(
        "work_centers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("capacity_qty", sa.Numeric(10, 2), nullable=False),
        sa.Column("capacity_days", sa.Numeric(6, 2), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_gate", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_work_centers_code", "work_centers", ["code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_work_centers_code", table_name="work_centers")
    op.drop_table("work_centers")
    op.drop_index("ix_attachments_item_id", table_name="attachments")
    op.drop_table("attachments")
    sa.Enum(name="attachment_store").drop(op.get_bind(), checkfirst=True)
    op.drop_column("order_items", "construction_done_at")
    op.drop_column("order_items", "procurement_needed")
