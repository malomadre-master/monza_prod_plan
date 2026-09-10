from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import settings

ALLOWED_SUFFIXES = {
    ".doc",
    ".docx",
    ".pdf",
    ".dxf",
    ".dwg",
    ".xls",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}
MAX_BYTES = 50 * 1024 * 1024
INLINE_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


def attachments_root() -> Path:
    path = Path(settings.attachments_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_upload(file: UploadFile, payload: bytes) -> str:
    name = Path(file.filename or "file").name
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Формат {suffix or 'без расширения'} не разрешён",
        )
    if len(payload) > MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл больше 50 МБ")
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой файл")
    return name


def store_file(item_id: int, store: str, original_name: str, payload: bytes) -> str:
    suffix = Path(original_name).suffix.lower()
    stored = f"{uuid4().hex}{suffix}"
    folder = attachments_root() / str(item_id) / store
    folder.mkdir(parents=True, exist_ok=True)
    (folder / stored).write_bytes(payload)
    return stored


def file_path(item_id: int, store: str, stored_name: str) -> Path:
    return attachments_root() / str(item_id) / store / stored_name
