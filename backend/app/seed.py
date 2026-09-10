from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, UserRole, WorkCenter
from app.security import hash_password

DEFAULT_CENTERS = [
    ("construction", "Конструирование", "item", "1", "2", 10, False),
    ("complectation", "Комплектация", "order", "4", "1", 20, True),
    ("saw", "Пила", "m2", "100", "1", 30, False),
    ("edgebanding", "Кромкооблицовка", "linear_m", "500", "1", 40, False),
    ("drilling", "Присадка", "m2", "140", "1", 50, False),
    ("milling", "Фрезерование", "m2", "30", "1", 60, False),
    ("assembly", "Сборка", "m2", "80", "1", 70, False),
    ("qc", "ОТК", "m2", "80", "1", 80, False),
]


def seed_admin(db: Session) -> None:
    if db.query(User).count() > 0:
        return
    db.add(
        User(
            username=settings.bootstrap_admin_username,
            display_name=settings.bootstrap_admin_name,
            password_hash=hash_password(settings.bootstrap_admin_password),
            role=UserRole.admin,
            is_active=True,
        )
    )
    db.commit()


def seed_work_centers(db: Session) -> None:
    if db.query(WorkCenter).count() > 0:
        return
    for code, title, unit, qty, days, sort, gate in DEFAULT_CENTERS:
        db.add(
            WorkCenter(
                code=code,
                title=title,
                unit=unit,
                capacity_qty=Decimal(qty),
                capacity_days=Decimal(days),
                sort_order=sort,
                is_gate=gate,
            )
        )
    db.commit()
