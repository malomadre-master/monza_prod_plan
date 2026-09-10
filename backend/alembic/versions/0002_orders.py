from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_orders"
down_revision: Union[str, None] = "0001_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer", sa.String(length=200), nullable=False),
        sa.Column("contract_number", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("contract_date", sa.Date(), nullable=False),
        sa.Column("launch_date", sa.Date(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "status",
            sa.Enum("draft", "queued", name="order_status"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("claimed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_orders_customer", "orders", ["customer"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "item_type",
            sa.Enum("kitchen", "wardrobe", "cabinet", "hallway", "mirror", "appliance", "other", name="item_type"),
            nullable=False,
        ),
        sa.Column("comment", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("constructor_coeff", sa.Numeric(4, 2), nullable=False, server_default="1.00"),
        sa.Column("area_m2", sa.Numeric(10, 2), nullable=False),
        sa.Column("linear_m", sa.Numeric(10, 2), nullable=False),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_customer", table_name="orders")
    op.drop_table("orders")
    sa.Enum(name="item_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="order_status").drop(op.get_bind(), checkfirst=True)
