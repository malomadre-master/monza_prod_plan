from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.catalog import WORK_CENTER_CODES
from app.db import get_db
from app.deps import get_current_user
from app.models import (
    AttachmentStore,
    Order,
    OrderItem,
    OrderStatus,
    User,
    UserRole,
    WorkEvent,
    WorkEventKind,
)
from app.schemas import TerminalCardOut, TerminalFileOut, TerminalQueueOut, WorkEventIn, WorkEventOut
from scheduler.models import SHOP_ROUTE

router = APIRouter(prefix="/api/terminal", tags=["terminal"])

PREV_SHOP = {code: (None if index == 0 else SHOP_ROUTE[index - 1]) for index, code in enumerate(SHOP_ROUTE)}
TERMINAL_ROLES = {UserRole.admin, UserRole.planner, UserRole.supply, UserRole.worker}


def _resolve_center(user: User, requested: str | None) -> str:
    if requested and requested not in WORK_CENTER_CODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестный участок")
    if user.role in (UserRole.admin, UserRole.planner):
        return requested or user.work_center_code or "saw"
    if user.role == UserRole.supply:
        center = requested or "complectation"
        if center != "complectation":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Снабжение работает на Комплектации")
        return center
    if user.role == UserRole.worker:
        if not user.work_center_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Задайте участок сотруднику")
        if requested and requested != user.work_center_code:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Это не ваш участок")
        return user.work_center_code
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Терминал только для цеха")


def _event_map(db: Session, item_ids: list[int]) -> dict[tuple[int, str, WorkEventKind], WorkEvent]:
    if not item_ids:
        return {}
    rows = (
        db.query(WorkEvent)
        .options(joinedload(WorkEvent.user))
        .filter(WorkEvent.item_id.in_(item_ids))
        .all()
    )
    return {(row.item_id, row.center_code, row.kind): row for row in rows}


def _open_taken(db: Session, user_id: int, center: str) -> list[WorkEvent]:
    taken = (
        db.query(WorkEvent)
        .filter(
            WorkEvent.user_id == user_id,
            WorkEvent.center_code == center,
            WorkEvent.kind == WorkEventKind.taken,
        )
        .all()
    )
    if not taken:
        return []
    done_ids = {
        row.item_id
        for row in db.query(WorkEvent).filter(
            WorkEvent.item_id.in_([row.item_id for row in taken]),
            WorkEvent.center_code == center,
            WorkEvent.kind == WorkEventKind.done,
        )
    }
    return [row for row in taken if row.item_id not in done_ids]


def _ready_for_center(item: OrderItem, center: str, events: dict[tuple[int, str, WorkEventKind], WorkEvent]) -> bool:
    if item.construction_done_at is None:
        return False
    if center == "complectation":
        if item.procurement_needed is not True:
            return False
        return (item.id, "complectation", WorkEventKind.materials_confirmed) not in events
    if center not in PREV_SHOP:
        return False
    if (item.id, center, WorkEventKind.done) in events:
        return False
    if item.procurement_needed is True:
        if (item.id, "complectation", WorkEventKind.materials_confirmed) not in events:
            return False
    previous = PREV_SHOP[center]
    if previous is None:
        return True
    return (item.id, previous, WorkEventKind.done) in events


def _card(item: OrderItem, center: str, events: dict[tuple[int, str, WorkEventKind], WorkEvent], user: User) -> TerminalCardOut:
    taken = events.get((item.id, center, WorkEventKind.taken))
    if center == "complectation":
        step = "waiting"
        taken_id = None
        taken_name = None
    elif taken and events.get((item.id, center, WorkEventKind.done)) is None:
        mine = taken.user_id == user.id
        step = "mine" if mine else "taken"
        taken_id = taken.user_id
        taken_name = taken.user.display_name if taken.user else None
    else:
        step = "waiting"
        taken_id = None
        taken_name = None
    store = AttachmentStore.procurement if center == "complectation" else AttachmentStore.production
    files = [
        TerminalFileOut(
            id=att.id,
            original_name=att.original_name,
            store=att.store,
            content_type=att.content_type,
            size_bytes=att.size_bytes,
        )
        for att in item.attachments
        if att.store == store
    ]
    return TerminalCardOut(
        order_id=item.order_id,
        item_id=item.id,
        customer=item.order.customer,
        item_type=item.item_type,
        comment=item.comment,
        qty=item.qty,
        area_m2=item.area_m2,
        linear_m=item.linear_m,
        order_priority=item.order.priority,
        item_priority=item.priority,
        launch_date=item.order.launch_date,
        center_code=center,
        step_status=step,
        taken_by_id=taken_id,
        taken_by_name=taken_name,
        files=files,
    )


@router.get("/queue", response_model=TerminalQueueOut)
def terminal_queue(
    center: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TerminalQueueOut:
    if user.role not in TERMINAL_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Терминал только для цеха")
    resolved = _resolve_center(user, center)
    items = (
        db.query(OrderItem)
        .join(Order)
        .options(joinedload(OrderItem.order), joinedload(OrderItem.attachments))
        .filter(OrderItem.construction_done_at.isnot(None), Order.status != OrderStatus.draft)
        .all()
    )
    events = _event_map(db, [item.id for item in items])
    ready = [item for item in items if _ready_for_center(item, resolved, events)]
    ready.sort(key=lambda item: (item.order.priority, item.priority, item.order.launch_date, item.id))
    cards = [_card(item, resolved, events, user) for item in ready]
    return TerminalQueueOut(center_code=resolved, cards=cards)


@router.post("/events", response_model=WorkEventOut, status_code=status.HTTP_201_CREATED)
def post_event(
    payload: WorkEventIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkEvent:
    if user.role not in TERMINAL_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Терминал только для цеха")
    center = _resolve_center(user, payload.center_code)
    item = (
        db.query(OrderItem)
        .options(joinedload(OrderItem.order), joinedload(OrderItem.attachments))
        .filter(OrderItem.id == payload.item_id, OrderItem.order_id == payload.order_id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Изделие не найдено")
    events = _event_map(db, [item.id])
    if payload.kind == WorkEventKind.materials_confirmed:
        if center != "complectation":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Подтверждение только на Комплектации")
        if not _ready_for_center(item, "complectation", events):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Изделие ещё не на Комплектации")
    elif payload.kind == WorkEventKind.taken:
        if center == "complectation":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="На Комплектации отмечают «всё в наличии»")
        if not _ready_for_center(item, center, events):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Изделие ещё не на этом участке")
        if (item.id, center, WorkEventKind.taken) in events:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Уже взяли")
        if user.role != UserRole.admin and _open_taken(db, user.id, center):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Сначала завершите текущее изделие")
    elif payload.kind == WorkEventKind.done:
        if center == "complectation":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="На Комплектации отмечают «всё в наличии»")
        taken = events.get((item.id, center, WorkEventKind.taken))
        if taken is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Сначала возьмите изделие")
        if taken.user_id != user.id and user.role != UserRole.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Завершает тот, кто взял")
        if (item.id, center, WorkEventKind.done) in events:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Уже готово")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестное событие")

    row = WorkEvent(
        item_id=item.id,
        center_code=center,
        kind=payload.kind,
        user_id=user.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Событие уже есть")
    db.refresh(row)
    return row
