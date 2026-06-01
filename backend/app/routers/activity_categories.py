from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ActivityCategory
from app.routers.common import apply_updates, commit_or_400, get_or_404
from app.schemas import ActivityCategoryCreate, ActivityCategoryRead, ActivityCategoryUpdate


router = APIRouter()


@router.get("", response_model=list[ActivityCategoryRead])
def list_activity_categories(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[ActivityCategory]:
    return list(db.scalars(select(ActivityCategory).offset(skip).limit(limit)))


@router.post("", response_model=ActivityCategoryRead)
def create_activity_category(
    payload: ActivityCategoryCreate,
    db: Session = Depends(get_db),
) -> ActivityCategory:
    if db.scalar(select(ActivityCategory).where(ActivityCategory.name == payload.name)):
        raise HTTPException(status_code=400, detail="category name already exists")
    category = ActivityCategory(**payload.model_dump())
    db.add(category)
    commit_or_400(db, "Could not create activity category")
    db.refresh(category)
    return category


@router.get("/{category_id}", response_model=ActivityCategoryRead)
def get_activity_category(
    category_id: UUID,
    db: Session = Depends(get_db),
) -> ActivityCategory:
    return get_or_404(db, ActivityCategory, category_id, "Activity category")


@router.patch("/{category_id}", response_model=ActivityCategoryRead)
def update_activity_category(
    category_id: UUID,
    payload: ActivityCategoryUpdate,
    db: Session = Depends(get_db),
) -> ActivityCategory:
    category = get_or_404(db, ActivityCategory, category_id, "Activity category")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        duplicate = db.scalar(
            select(ActivityCategory).where(
                ActivityCategory.name == data["name"],
                ActivityCategory.id != category_id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=400, detail="category name already exists")
    apply_updates(category, payload)
    commit_or_400(db, "Could not update activity category")
    db.refresh(category)
    return category


@router.delete("/{category_id}", response_model=ActivityCategoryRead)
def delete_activity_category(
    category_id: UUID,
    db: Session = Depends(get_db),
) -> ActivityCategory:
    category = get_or_404(db, ActivityCategory, category_id, "Activity category")
    db.delete(category)
    commit_or_400(db, "Could not delete activity category")
    return category

