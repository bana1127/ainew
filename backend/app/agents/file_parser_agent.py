from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.file import UploadedFile


@dataclass
class FileParserResult:
    file_names: list[str] = field(default_factory=list)
    file_types: list[str] = field(default_factory=list)
    # TODO(Task 8): Add image content analysis results here


@dataclass
class ReceiptFileInfo:
    file_id: UUID | None
    file_name: str
    mime_type: str | None
    file_exists: bool = False


class FileParserAgent:
    def __init__(self, db: Session):
        self.db = db

    def parse(self, file_ids: list[UUID]) -> FileParserResult:
        if not file_ids:
            return FileParserResult()

        files = self.db.execute(
            select(UploadedFile).where(UploadedFile.id.in_(file_ids))
        ).scalars().all()

        file_names = [f.original_filename for f in files if f.original_filename]
        file_types = [f.file_type or f.mime_type or "unknown" for f in files]

        # TODO(Task 8): Add image/document content analysis using multimodal model

        return FileParserResult(file_names=file_names, file_types=file_types)

    def parse_receipt_file(self, file_id: UUID) -> ReceiptFileInfo:
        """Retrieve UploadedFile metadata for receipt analysis."""
        from app.core.config import settings
        from pathlib import Path

        uploaded = self.db.get(UploadedFile, file_id)
        if uploaded is None:
            return ReceiptFileInfo(file_id=file_id, file_name="", mime_type=None, file_exists=False)

        # Resolve absolute path
        full_path = settings.UPLOAD_DIR.parent / uploaded.stored_path
        file_exists = Path(full_path).exists()

        return ReceiptFileInfo(
            file_id=file_id,
            file_name=uploaded.original_filename,
            mime_type=uploaded.mime_type,
            file_exists=file_exists,
        )
