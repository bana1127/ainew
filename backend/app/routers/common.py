from typing import Any, TypeVar

from fastapi import HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


ModelT = TypeVar("ModelT")


def pagination_params(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> tuple[int, int]:
    return skip, limit


def get_or_404(db: Session, model: type[ModelT], item_id: Any, label: str) -> ModelT:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return item


def apply_updates(item: Any, payload: Any) -> Any:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    return item


def commit_or_400(db: Session, detail: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=detail) from exc


def scalar_exists(db: Session, model: type[ModelT], condition: Any) -> bool:
    return db.scalar(select(model).where(condition)) is not None

