from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.catalog import ORDER_CREATE_ROLES, WORK_CENTER_CODES
from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import (
    Attendance,
    CalendarDay,
    CalendarDayKind,
    Order,
    OrderItem,
    OrderStatus,
    SchedulePin,
    User,
    UserRole,
    WorkCenter,
    WorkEvent,
    WorkEventKind,
)
from app.schemas import BoardCardOut, PinIn, PlanDiffRow, PlanPreviewOut, PlanSlotOut, QueueReorderIn
from scheduler.engine import plan_jobs
from scheduler.models import SHOP_ROUTE, CenterSpec, ConstructorSpec, Job, Pin

router = APIRouter(prefix="/api", tags=["plan"])


def _db_pins(db: Session) -> list[Pin]:
    return [Pin(row.item_id, row.center_code, row.start, row.finish) for row in db.query(SchedulePin).all()]


def _plan_slots(
    db: Session,
    pins: list[Pin] | None = None,
    priority_overrides: dict[int, tuple[int, int]] | None = None,
) -> list[PlanSlotOut]:
    centers = [
        CenterSpec(
            code=row.code,
            unit=row.unit,
            capacity_qty=row.capacity_qty,
            capacity_days=row.capacity_days,
            is_gate=row.is_gate,
        )
        for row in db.query(WorkCenter).order_by(WorkCenter.sort_order, WorkCenter.id).all()
    ]
    designers = (
        db.query(User)
        .filter(User.role == UserRole.designer, User.is_active.is_(True))
        .order_by(User.id)
        .all()
    )
    constructors = [
        ConstructorSpec(id=row.id, efficiency=row.efficiency or Decimal("1"))
        for row in designers
    ]
    holidays = {
        row.day for row in db.query(CalendarDay).filter(CalendarDay.kind == CalendarDayKind.holiday).all()
    }
    extra_work = {
        row.day for row in db.query(CalendarDay).filter(CalendarDay.kind == CalendarDayKind.extra_work).all()
    }
    absences: dict[int, set] = defaultdict(set)
    for mark in db.query(Attendance).filter(Attendance.present.is_(False)).all():
        absences[mark.user_id].add(mark.day)
    staff_rows = (
        db.query(User)
        .filter(User.is_active.is_(True), User.role.in_([UserRole.supply, UserRole.worker]))
        .all()
    )
    center_staff: dict[str, list[tuple[int, Decimal]]] = defaultdict(list)
    for row in staff_rows:
        code = row.work_center_code
        if not code:
            if row.role == UserRole.supply:
                code = "complectation"
            else:
                continue
        center_staff[code].append((row.id, row.efficiency or Decimal("1")))
    orders = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.status != OrderStatus.draft)
        .all()
    )
    confirmed: dict[int, date] = {}
    for event in db.query(WorkEvent).filter(WorkEvent.kind == WorkEventKind.materials_confirmed).all():
        confirmed[event.item_id] = event.created_at.date()
    jobs: list[Job] = []
    names: dict[int, str] = {}
    item_meta: dict[int, tuple] = {}
    for order in orders:
        names[order.id] = order.customer
        for item in order.items:
            needed = True if item.procurement_needed is None else item.procurement_needed
            order_priority, item_priority = order.priority, item.priority
            if priority_overrides and item.id in priority_overrides:
                order_priority, item_priority = priority_overrides[item.id]
            item_meta[item.id] = (item.item_type, item.qty, order_priority, item_priority, order.launch_date)
            jobs.append(
                Job(
                    order_id=order.id,
                    item_id=item.id,
                    order_priority=order_priority,
                    item_priority=item_priority,
                    launch_date=order.launch_date,
                    contract_date=order.contract_date,
                    qty=item.qty,
                    area_m2=item.area_m2,
                    linear_m=item.linear_m,
                    procurement_needed=needed,
                    construction_done=item.construction_done_at.date() if item.construction_done_at else None,
                    materials_confirmed=confirmed.get(item.id),
                )
            )
    pin_list = pins if pins is not None else _db_pins(db)
    pin_keys = {(row.item_id, row.center_code) for row in pin_list}
    slots = plan_jobs(
        jobs,
        constructors=constructors or None,
        centers=centers,
        holidays=holidays or None,
        extra_work=extra_work or None,
        absences=dict(absences) or None,
        center_staff=dict(center_staff) or None,
        pins=pin_list or None,
    )
    result: list[PlanSlotOut] = []
    for slot in slots:
        item_type, qty, order_priority, item_priority, launch_date = item_meta[slot.item_id]
        result.append(
            PlanSlotOut(
                order_id=slot.order_id,
                item_id=slot.item_id,
                customer=names[slot.order_id],
                center_code=slot.center_code,
                volume=slot.volume,
                start=slot.start,
                finish=slot.finish,
                item_type=item_type,
                qty=qty,
                order_priority=order_priority,
                item_priority=item_priority,
                launch_date=launch_date,
                pinned=slot.pinned or (slot.item_id, slot.center_code) in pin_keys,
            )
        )
    return result


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


def _board_step(
    item: OrderItem, events: dict[tuple[int, str, WorkEventKind], WorkEvent]
) -> tuple[str, str, str | None]:
    order = item.order
    if item.construction_done_at is None:
        if order.claimed_by_id:
            name = order.claimed_by.display_name if order.claimed_by else None
            return "construction", "in_progress", name
        return "construction", "waiting", None
    needed = True if item.procurement_needed is None else item.procurement_needed
    if needed and (item.id, "complectation", WorkEventKind.materials_confirmed) not in events:
        return "complectation", "waiting", None
    for center in SHOP_ROUTE:
        if (item.id, center, WorkEventKind.done) in events:
            continue
        taken = events.get((item.id, center, WorkEventKind.taken))
        if taken:
            name = taken.user.display_name if taken.user else None
            return center, "in_progress", name
        return center, "waiting", None
    return "qc", "done", None


@router.get("/plan", response_model=list[PlanSlotOut])
def get_plan(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[PlanSlotOut]:
    return _plan_slots(db)


@router.get("/plan/board", response_model=list[BoardCardOut])
def get_plan_board(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[BoardCardOut]:
    slots = {(row.item_id, row.center_code): row for row in _plan_slots(db)}
    orders = (
        db.query(Order)
        .options(selectinload(Order.items), joinedload(Order.claimed_by))
        .filter(Order.status != OrderStatus.draft)
        .all()
    )
    items = [item for order in orders for item in order.items]
    events = _event_map(db, [item.id for item in items])
    cards: list[BoardCardOut] = []
    for item in items:
        center, board_status, taken_by = _board_step(item, events)
        planned = slots.get((item.id, center))
        cards.append(
            BoardCardOut(
                order_id=item.order_id,
                item_id=item.id,
                customer=item.order.customer,
                item_type=item.item_type,
                qty=item.qty,
                comment=item.comment,
                order_priority=item.order.priority,
                item_priority=item.priority,
                launch_date=item.order.launch_date,
                order_status=item.order.status,
                center_code=center,
                board_status=board_status,
                taken_by_name=taken_by,
                start=planned.start if planned else None,
                finish=planned.finish if planned else None,
                volume=planned.volume if planned else None,
            )
        )
    cards.sort(
        key=lambda row: (
            row.order_priority,
            row.item_priority,
            row.launch_date,
            row.order_id,
            row.item_id,
        )
    )
    return cards


def _plan_diff(before: list[PlanSlotOut], after: list[PlanSlotOut]) -> list[PlanDiffRow]:
    before_map = {(row.item_id, row.center_code): row for row in before}
    after_map = {(row.item_id, row.center_code): row for row in after}
    keys = sorted(set(before_map) | set(after_map))
    changes: list[PlanDiffRow] = []
    for key in keys:
        old = before_map.get(key)
        new = after_map.get(key)
        if old is None or new is None or old.start != new.start or old.finish != new.finish:
            src = new or old
            assert src is not None
            changes.append(
                PlanDiffRow(
                    order_id=src.order_id,
                    item_id=src.item_id,
                    customer=src.customer,
                    center_code=src.center_code,
                    before_start=old.start if old else None,
                    before_finish=old.finish if old else None,
                    after_start=new.start if new else None,
                    after_finish=new.finish if new else None,
                )
            )
    return changes


def _resolve_pin_dates(payload: PinIn, current: list[PlanSlotOut]) -> tuple[date, date]:
    found = next(
        (row for row in current if row.item_id == payload.item_id and row.center_code == payload.center_code),
        None,
    )
    start = payload.start or (found.start if found else None)
    finish = payload.finish or (found.finish if found else None)
    if start is None or finish is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Нет слота для закрепления")
    if finish < start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Финиш раньше старта")
    return start, finish


def _proposed_pins(db: Session, payload: PinIn, current: list[PlanSlotOut]) -> list[Pin]:
    existing = [row for row in _db_pins(db) if not (row.item_id == payload.item_id and row.center_code == payload.center_code)]
    if payload.remove:
        return existing
    start, finish = _resolve_pin_dates(payload, current)
    existing.append(Pin(payload.item_id, payload.center_code, start, finish))
    return existing


def _require_item(db: Session, payload: PinIn) -> OrderItem:
    if payload.center_code not in WORK_CENTER_CODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестный участок")
    item = db.query(OrderItem).options(joinedload(OrderItem.order)).filter(OrderItem.id == payload.item_id).one_or_none()
    if item is None or item.order.status == OrderStatus.draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Изделие не найдено")
    return item


@router.post("/plan/pins/preview", response_model=PlanPreviewOut)
def preview_pin(
    payload: PinIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*ORDER_CREATE_ROLES)),
) -> PlanPreviewOut:
    _require_item(db, payload)
    current = _plan_slots(db)
    proposed = _plan_slots(db, pins=_proposed_pins(db, payload, current))
    return PlanPreviewOut(changes=_plan_diff(current, proposed), slots=proposed)


@router.put("/plan/pins", response_model=PlanPreviewOut)
def apply_pin(
    payload: PinIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*ORDER_CREATE_ROLES)),
) -> PlanPreviewOut:
    item = _require_item(db, payload)
    current = _plan_slots(db)
    proposed_pins = _proposed_pins(db, payload, current)
    row = (
        db.query(SchedulePin)
        .filter(SchedulePin.item_id == payload.item_id, SchedulePin.center_code == payload.center_code)
        .one_or_none()
    )
    if payload.remove:
        if row is not None:
            db.delete(row)
            db.commit()
    else:
        start, finish = _resolve_pin_dates(payload, current)
        if row is None:
            db.add(
                SchedulePin(
                    item_id=item.id,
                    center_code=payload.center_code,
                    start=start,
                    finish=finish,
                    created_by_id=user.id,
                )
            )
        else:
            row.start = start
            row.finish = finish
        db.commit()
    after = _plan_slots(db, pins=proposed_pins)
    return PlanPreviewOut(changes=_plan_diff(current, after), slots=after)


@router.delete("/plan/pins/{item_id}/{center_code}", response_model=PlanPreviewOut)
def delete_pin(
    item_id: int,
    center_code: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*ORDER_CREATE_ROLES)),
) -> PlanPreviewOut:
    return apply_pin(PinIn(item_id=item_id, center_code=center_code, remove=True), db, user)


def _queue_priority_overrides(db: Session, payload: QueueReorderIn) -> dict[int, tuple[int, int]]:
    if payload.center_code not in WORK_CENTER_CODES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неизвестный участок")
    if len(payload.item_ids) != len(set(payload.item_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Повторы в очереди")
    orders = (
        db.query(Order)
        .options(selectinload(Order.items), joinedload(Order.claimed_by))
        .filter(Order.status != OrderStatus.draft)
        .all()
    )
    items_by_id = {item.id: item for order in orders for item in order.items}
    missing = [item_id for item_id in payload.item_ids if item_id not in items_by_id]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Изделие не найдено")
    events = _event_map(db, list(items_by_id))
    waiting = [
        item.id
        for item in items_by_id.values()
        if _board_step(item, events)[:2] == (payload.center_code, "waiting")
    ]
    if sorted(payload.item_ids) != sorted(waiting):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Перетаскивать можно только очередь ожидания этого участка",
        )
    order_rank: dict[int, int] = {}
    next_rank = 1
    item_rank: dict[int, int] = {}
    per_order = defaultdict(int)
    for item_id in payload.item_ids:
        item = items_by_id[item_id]
        if item.order_id not in order_rank:
            order_rank[item.order_id] = min(next_rank, 9)
            next_rank += 1
        per_order[item.order_id] += 1
        item_rank[item_id] = min(per_order[item.order_id], 9)
    overrides: dict[int, tuple[int, int]] = {}
    for item in items_by_id.values():
        if item.order_id in order_rank:
            overrides[item.id] = (order_rank[item.order_id], item_rank.get(item.id, item.priority))
    return overrides


def _apply_queue_priorities(db: Session, payload: QueueReorderIn, overrides: dict[int, tuple[int, int]]) -> None:
    if not payload.item_ids:
        return
    items = (
        db.query(OrderItem)
        .options(joinedload(OrderItem.order))
        .filter(OrderItem.id.in_(payload.item_ids))
        .all()
    )
    seen_orders: set[int] = set()
    for item in items:
        order_priority, item_priority = overrides[item.id]
        item.priority = item_priority
        if item.order_id not in seen_orders:
            item.order.priority = order_priority
            seen_orders.add(item.order_id)
    db.commit()


@router.post("/plan/queue/preview", response_model=PlanPreviewOut)
def preview_queue(
    payload: QueueReorderIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*ORDER_CREATE_ROLES)),
) -> PlanPreviewOut:
    overrides = _queue_priority_overrides(db, payload)
    current = _plan_slots(db)
    proposed = _plan_slots(db, priority_overrides=overrides)
    return PlanPreviewOut(changes=_plan_diff(current, proposed), slots=proposed)


@router.put("/plan/queue", response_model=PlanPreviewOut)
def apply_queue(
    payload: QueueReorderIn,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*ORDER_CREATE_ROLES)),
) -> PlanPreviewOut:
    overrides = _queue_priority_overrides(db, payload)
    current = _plan_slots(db)
    _apply_queue_priorities(db, payload, overrides)
    after = _plan_slots(db)
    return PlanPreviewOut(changes=_plan_diff(current, after), slots=after)
