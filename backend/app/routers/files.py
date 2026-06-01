from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import UploadedFile
from app.routers.common import commit_or_400, get_or_404
from app.schemas import UploadedFileRead


router = APIRouter()


@router.post("/upload", response_model=UploadedFileRead)
def upload_file(
    file: UploadFile = File(...),
    file_type: str | None = Form(default=None),
    related_entity_type: str | None = Form(default=None),
    related_entity_id: UUID | None = Form(default=None),
    db: Session = Depends(get_db),
) -> UploadedFile:
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix
    stored_name = f"{uuid4()}{suffix}"
    stored_path = settings.UPLOAD_DIR / stored_name

    with stored_path.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            output.write(chunk)

    record = UploadedFile(
        original_filename=file.filename or stored_name,
        stored_path=(Path("uploads") / stored_name).as_posix(),
        mime_type=file.content_type,
        file_type=file_type,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(record)
    commit_or_400(db, "Could not save uploaded file metadata")
    db.refresh(record)
    return record


@router.get("", response_model=list[UploadedFileRead])
def list_files(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    file_type: str | None = None,
    db: Session = Depends(get_db),
) -> list[UploadedFile]:
    statement = select(UploadedFile)
    if file_type:
        statement = statement.where(UploadedFile.file_type == file_type)
    return list(db.scalars(statement.offset(skip).limit(limit)))


@router.get("/{file_id}", response_model=UploadedFileRead)
def get_file(file_id: UUID, db: Session = Depends(get_db)) -> UploadedFile:
    return get_or_404(db, UploadedFile, file_id, "File")


@router.delete("/{file_id}", response_model=UploadedFileRead)
def delete_file(file_id: UUID, db: Session = Depends(get_db)) -> UploadedFile:
    record = get_or_404(db, UploadedFile, file_id, "File")
    stored_path = Path(record.stored_path)
    if not stored_path.is_absolute():
        stored_path = settings.UPLOAD_DIR.parent / stored_path
    if stored_path.exists() and stored_path.is_file():
        stored_path.unlink()
    db.delete(record)
    commit_or_400(db, "Could not delete file")
    return record
