from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.models import OrderItem, SchedulePin, WorkEvent, WorkEventKind


def step_in_progress(db: Session, item_id: int, center_code: str) -> bool:
    item = (
        db.query(OrderItem)
        .options(joinedload(OrderItem.order))
        .filter(OrderItem.id == item_id)
        .one_or_none()
    )
    if item is None:
        return False
    if center_code == "construction":
        return item.construction_done_at is None and item.order.claimed_by_id is not None
    events = {
        row.kind
        for row in db.query(WorkEvent).filter(WorkEvent.item_id == item_id, WorkEvent.center_code == center_code)
    }
    if center_code == "complectation":
        return False
    return WorkEventKind.taken in events and WorkEventKind.done not in events


def pin_slot(db: Session, item_id: int, center_code: str, start: date, finish: date, user_id: int) -> None:
    existing = (
        db.query(SchedulePin)
        .filter(SchedulePin.item_id == item_id, SchedulePin.center_code == center_code)
        .one_or_none()
    )
    if existing is not None:
        return
    db.add(
        SchedulePin(
            item_id=item_id,
            center_code=center_code,
            start=start,
            finish=finish,
            created_by_id=user_id,
        )
    )


def unpin_slot(db: Session, item_id: int, center_code: str) -> None:
    row = (
        db.query(SchedulePin)
        .filter(SchedulePin.item_id == item_id, SchedulePin.center_code == center_code)
        .one_or_none()
    )
    if row is not None:
        db.delete(row)


def pin_from_plan(db: Session, item_id: int, center_code: str, user_id: int) -> None:
    from app.routers.plan import _plan_slots

    slot = next((row for row in _plan_slots(db) if row.item_id == item_id and row.center_code == center_code), None)
    if slot is None:
        today = date.today()
        pin_slot(db, item_id, center_code, today, today, user_id)
        return
    pin_slot(db, item_id, center_code, slot.start, slot.finish, user_id)
