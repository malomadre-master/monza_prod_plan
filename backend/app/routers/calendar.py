from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.catalog import CALENDAR_ROLES, STAFF_ROLES
from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import Attendance, CalendarDay, User, UserRole
from app.schemas import (
    AttendanceMarkOut,
    AttendanceMonthOut,
    AttendancePutIn,
    CalendarDayIn,
    CalendarDayOut,
    StaffOut,
)

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


def _staff_query(db: Session):
    return (
        db.query(User)
        .filter(User.is_active.is_(True), User.role.in_([UserRole(role) for role in STAFF_ROLES]))
        .order_by(User.role, User.id)
    )


@router.get("/days", response_model=list[CalendarDayOut])
def list_days(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CalendarDay]:
    if date_to < date_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный период")
    return (
        db.query(CalendarDay)
        .filter(CalendarDay.day >= date_from, CalendarDay.day <= date_to)
        .order_by(CalendarDay.day)
        .all()
    )


@router.post("/days", response_model=CalendarDayOut, status_code=status.HTTP_201_CREATED)
def upsert_day(
    payload: CalendarDayIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*CALENDAR_ROLES)),
) -> CalendarDay:
    row = db.query(CalendarDay).filter(CalendarDay.day == payload.day).one_or_none()
    if row is None:
        row = CalendarDay(day=payload.day, kind=payload.kind, title=payload.title.strip())
        db.add(row)
    else:
        row.kind = payload.kind
        row.title = payload.title.strip()
    db.commit()
    db.refresh(row)
    return row


@router.delete("/days/{day}", status_code=status.HTTP_204_NO_CONTENT)
def delete_day(
    day: date,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*CALENDAR_ROLES)),
) -> None:
    row = db.query(CalendarDay).filter(CalendarDay.day == day).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="День не найден")
    db.delete(row)
    db.commit()


@router.get("/staff", response_model=list[StaffOut])
def list_staff(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*CALENDAR_ROLES)),
) -> list[User]:
    return _staff_query(db).all()


@router.get("/attendance", response_model=AttendanceMonthOut)
def list_attendance(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*CALENDAR_ROLES)),
) -> AttendanceMonthOut:
    if date_to < date_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный период")
    staff = _staff_query(db).all()
    rows = (
        db.query(Attendance)
        .filter(Attendance.day >= date_from, Attendance.day <= date_to, Attendance.present.is_(False))
        .all()
    )
    return AttendanceMonthOut(
        staff=[StaffOut.model_validate(user) for user in staff],
        absences=[AttendanceMarkOut(user_id=row.user_id, day=row.day, present=False) for row in rows],
    )


@router.put("/attendance", response_model=AttendanceMarkOut)
def put_attendance(
    payload: AttendancePutIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*CALENDAR_ROLES)),
) -> AttendanceMarkOut:
    user = db.get(User, payload.user_id)
    if user is None or not user.is_active or user.role.value not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден")
    row = (
        db.query(Attendance)
        .filter(Attendance.user_id == payload.user_id, Attendance.day == payload.day)
        .one_or_none()
    )
    if payload.present:
        if row is not None:
            db.delete(row)
            db.commit()
        return AttendanceMarkOut(user_id=payload.user_id, day=payload.day, present=True)
    if row is None:
        row = Attendance(user_id=payload.user_id, day=payload.day, present=False)
        db.add(row)
    else:
        row.present = False
    db.commit()
    return AttendanceMarkOut(user_id=payload.user_id, day=payload.day, present=False)
