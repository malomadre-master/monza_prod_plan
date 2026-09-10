from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_calendar_attendance"
down_revision: Union[str, None] = "0004_user_efficiency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("work_center_code", sa.String(length=40), nullable=True))
    op.create_table(
        "calendar_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("kind", sa.Enum("holiday", "extra_work", name="calendar_day_kind"), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False, server_default=""),
    )
    op.create_index("ix_calendar_days_day", "calendar_days", ["day"], unique=True)
    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("present", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("user_id", "day", name="uq_attendance_user_day"),
    )
    op.create_index("ix_attendance_user_id", "attendance", ["user_id"])
    op.create_index("ix_attendance_day", "attendance", ["day"])


def downgrade() -> None:
    op.drop_index("ix_attendance_day", table_name="attendance")
    op.drop_index("ix_attendance_user_id", table_name="attendance")
    op.drop_table("attendance")
    op.drop_index("ix_calendar_days_day", table_name="calendar_days")
    op.drop_table("calendar_days")
    sa.Enum(name="calendar_day_kind").drop(op.get_bind(), checkfirst=True)
    op.drop_column("users", "work_center_code")
