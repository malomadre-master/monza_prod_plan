from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, UserRole
from app.security import hash_password


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
