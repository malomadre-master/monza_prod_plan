from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.deps import get_current_user
from app.models import Order, OrderStatus, User, UserRole, WorkCenter
from app.schemas import PlanSlotOut
from scheduler.engine import plan_jobs
from scheduler.models import CenterSpec, ConstructorSpec, Job

router = APIRouter(prefix="/api", tags=["plan"])


@router.get("/plan", response_model=list[PlanSlotOut])
def get_plan(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[PlanSlotOut]:
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
    orders = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.status != OrderStatus.draft)
        .all()
    )
    jobs: list[Job] = []
    names: dict[int, str] = {}
    for order in orders:
        names[order.id] = order.customer
        for item in order.items:
            needed = True if item.procurement_needed is None else item.procurement_needed
            jobs.append(
                Job(
                    order_id=order.id,
                    item_id=item.id,
                    order_priority=order.priority,
                    item_priority=item.priority,
                    launch_date=order.launch_date,
                    contract_date=order.contract_date,
                    qty=item.qty,
                    area_m2=item.area_m2,
                    linear_m=item.linear_m,
                    procurement_needed=needed,
                )
            )
    slots = plan_jobs(jobs, constructors=constructors or None, centers=centers)
    return [
        PlanSlotOut(
            order_id=slot.order_id,
            item_id=slot.item_id,
            customer=names[slot.order_id],
            center_code=slot.center_code,
            volume=slot.volume,
            start=slot.start,
            finish=slot.finish,
        )
        for slot in slots
    ]
