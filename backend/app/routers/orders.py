from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.catalog import ITEM_TYPES, ORDER_CREATE_ROLES
from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import Order, OrderItem, OrderStatus, User
from app.schemas import OrderIn, OrderItemOut, OrderListOut, OrderOut, linear_from_area

router = APIRouter(prefix="/api", tags=["orders"])


def _order_out(order: Order) -> OrderOut:
    items = [OrderItemOut.model_validate(item) for item in order.items]
    total_area = sum((item.area_m2 for item in order.items), Decimal("0"))
    total_qty = sum(item.qty for item in order.items)
    return OrderOut(
        id=order.id,
        customer=order.customer,
        contract_number=order.contract_number,
        contract_date=order.contract_date,
        launch_date=order.launch_date,
        priority=order.priority,
        status=order.status,
        notes=order.notes,
        created_by_id=order.created_by_id,
        claimed_by_id=order.claimed_by_id,
        created_at=order.created_at,
        items=items,
        total_area_m2=total_area,
        total_qty=total_qty,
    )


def _apply_items(order: Order, payload: OrderIn) -> None:
    order.items.clear()
    for row in payload.items:
        order.items.append(
            OrderItem(
                item_type=row.item_type,
                comment=row.comment.strip(),
                qty=row.qty,
                priority=row.priority,
                constructor_coeff=row.constructor_coeff,
                area_m2=row.area_m2,
                linear_m=linear_from_area(row.area_m2),
            )
        )


@router.get("/catalog/item-types")
def item_types(_: User = Depends(get_current_user)) -> list[dict]:
    return [
        {"value": row["value"], "label": row["label"], "coeff": str(row["coeff"])}
        for row in ITEM_TYPES
    ]


@router.get("/customers", response_model=list[str])
def customers(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[str]:
    rows = db.query(Order.customer).distinct().order_by(Order.customer).all()
    return [row[0] for row in rows if row[0]]


@router.get("/orders", response_model=list[OrderListOut])
def list_orders(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[OrderListOut]:
    orders = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.created_by))
        .order_by(Order.priority, Order.launch_date, Order.id)
        .all()
    )
    result: list[OrderListOut] = []
    for order in orders:
        total_area = sum((item.area_m2 for item in order.items), Decimal("0"))
        result.append(
            OrderListOut(
                id=order.id,
                customer=order.customer,
                contract_number=order.contract_number,
                contract_date=order.contract_date,
                launch_date=order.launch_date,
                priority=order.priority,
                status=order.status,
                item_count=len(order.items),
                total_area_m2=total_area,
                created_by_name=order.created_by.display_name,
            )
        )
    return result


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> OrderOut:
    order = db.query(Order).options(joinedload(Order.items)).filter(Order.id == order_id).one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return _order_out(order)


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*ORDER_CREATE_ROLES)),
) -> OrderOut:
    if payload.status not in (OrderStatus.draft, OrderStatus.queued):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя задать такой статус")
    order = Order(
        customer=payload.customer.strip(),
        contract_number=payload.contract_number.strip(),
        contract_date=payload.contract_date,
        launch_date=payload.launch_date,
        priority=payload.priority,
        status=payload.status,
        notes=payload.notes.strip(),
        created_by_id=user.id,
    )
    _apply_items(order, payload)
    db.add(order)
    db.commit()
    db.refresh(order)
    return _order_out(order)


@router.put("/orders/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    payload: OrderIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*ORDER_CREATE_ROLES)),
) -> OrderOut:
    order = db.query(Order).options(joinedload(Order.items)).filter(Order.id == order_id).one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    if order.status != OrderStatus.draft:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="В очередь уже нельзя править — только черновик")
    order.customer = payload.customer.strip()
    order.contract_number = payload.contract_number.strip()
    order.contract_date = payload.contract_date
    order.launch_date = payload.launch_date
    order.priority = payload.priority
    order.status = payload.status
    order.notes = payload.notes.strip()
    _apply_items(order, payload)
    db.commit()
    db.refresh(order)
    _ = user
    return _order_out(order)
