from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_roles
from app.models import User
from app.schemas import UserCreateIn, UserOut, UserPatchIn
from app.security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> User:
    username = payload.username.strip()
    if db.query(User).filter(User.username == username).one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Такой логин уже есть")
    user = User(
        username=username,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        efficiency=payload.efficiency,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def patch_user(
    user_id: int,
    payload: UserPatchIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден")
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.efficiency is not None:
        user.efficiency = payload.efficiency
    db.commit()
    db.refresh(user)
    return user
