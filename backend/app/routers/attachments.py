from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.deps import get_current_user
from app.files import INLINE_SUFFIXES, file_path, store_file, validate_upload
from app.models import Attachment, AttachmentStore, Order, OrderItem, OrderStatus, User, UserRole
from app.schemas import AttachmentOut, ItemCompleteIn, OrderOut
from app.routers.orders import _order_out

router = APIRouter(prefix="/api", tags=["attachments"])


def _item(db: Session, order_id: int, item_id: int) -> OrderItem:
    item = (
        db.query(OrderItem)
        .options(joinedload(OrderItem.order), joinedload(OrderItem.attachments))
        .filter(OrderItem.id == item_id, OrderItem.order_id == order_id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Изделие не найдено")
    return item


def _can_edit_docs(user: User, order: Order) -> bool:
    if user.role in (UserRole.admin, UserRole.planner):
        return True
    if user.role == UserRole.designer and order.claimed_by_id == user.id:
        return True
    return False


@router.get("/orders/{order_id}/items/{item_id}/attachments", response_model=list[AttachmentOut])
def list_attachments(
    order_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Attachment]:
    return _item(db, order_id, item_id).attachments


@router.post("/orders/{order_id}/items/{item_id}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    order_id: int,
    item_id: int,
    store: AttachmentStore = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Attachment:
    item = _item(db, order_id, item_id)
    if item.construction_done_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Изделие уже завершено")
    if not _can_edit_docs(user, item.order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Документы может класть взявший конструктор")
    payload = await file.read()
    original = validate_upload(file, payload)
    stored = store_file(item.id, store.value, original, payload)
    row = Attachment(
        item_id=item.id,
        store=store,
        original_name=original,
        stored_name=stored,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(payload),
        uploaded_by_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> FileResponse:
    row = db.get(Attachment, attachment_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")
    path = file_path(row.item_id, row.store.value, row.stored_name)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл отсутствует на диске")
    inline = path.suffix.lower() in INLINE_SUFFIXES
    return FileResponse(
        path,
        media_type=row.content_type,
        filename=row.original_name,
        content_disposition_type="inline" if inline else "attachment",
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    row = db.get(Attachment, attachment_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")
    item = db.get(OrderItem, row.item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Изделие не найдено")
    if item.construction_done_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Изделие уже завершено")
    if not _can_edit_docs(user, item.order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    path = file_path(row.item_id, row.store.value, row.stored_name)
    if path.exists():
        path.unlink()
    db.delete(row)
    db.commit()


@router.post("/orders/{order_id}/claim", response_model=OrderOut)
def claim_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderOut:
    if user.role not in (UserRole.designer, UserRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Взять заказ может конструктор")
    busy = (
        db.query(Order)
        .filter(Order.claimed_by_id == user.id, Order.status == OrderStatus.in_design)
        .first()
    )
    if busy and user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Сначала завершите текущий заказ")
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.claimed_by))
        .filter(Order.id == order_id)
        .one_or_none()
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    if order.status != OrderStatus.queued or order.claimed_by_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Заказ уже взяли")
    order.claimed_by_id = user.id
    order.status = OrderStatus.in_design
    db.commit()
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.claimed_by))
        .filter(Order.id == order_id)
        .one()
    )
    return _order_out(order)


@router.post("/orders/{order_id}/items/{item_id}/complete", response_model=OrderOut)
def complete_item(
    order_id: int,
    item_id: int,
    payload: ItemCompleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderOut:
    item = _item(db, order_id, item_id)
    if not _can_edit_docs(user, item.order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Завершает взявший конструктор")
    if item.construction_done_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Уже завершено")
    has_production = any(att.store == AttachmentStore.production for att in item.attachments)
    if not has_production:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нужен хотя бы один производственный документ")
    item.procurement_needed = payload.procurement_needed
    item.construction_done_at = datetime.now(timezone.utc)
    db.flush()
    remaining = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order_id, OrderItem.construction_done_at.is_(None))
        .count()
    )
    if remaining == 0:
        item.order.status = OrderStatus.in_production
    db.commit()
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.claimed_by))
        .filter(Order.id == order_id)
        .one()
    )
    return _order_out(order)
