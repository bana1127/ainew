from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AppSetting
from app.routers.common import apply_updates, commit_or_400
from app.schemas import AppSettingCreate, AppSettingRead, AppSettingUpdate


router = APIRouter()


def get_by_key(db: Session, key: str) -> AppSetting:
    setting = db.scalar(select(AppSetting).where(AppSetting.key == key))
    if setting is None:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting


@router.get("", response_model=list[AppSettingRead])
def list_settings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[AppSetting]:
    return list(db.scalars(select(AppSetting).offset(skip).limit(limit)))


@router.post("", response_model=AppSettingRead)
def create_setting(payload: AppSettingCreate, db: Session = Depends(get_db)) -> AppSetting:
    if db.scalar(select(AppSetting).where(AppSetting.key == payload.key)):
        raise HTTPException(status_code=400, detail="setting key already exists")
    setting = AppSetting(**payload.model_dump())
    db.add(setting)
    commit_or_400(db, "Could not create setting")
    db.refresh(setting)
    return setting


@router.get("/{key}", response_model=AppSettingRead)
def get_setting(key: str, db: Session = Depends(get_db)) -> AppSetting:
    return get_by_key(db, key)


@router.patch("/{key}", response_model=AppSettingRead)
def update_setting(
    key: str,
    payload: AppSettingUpdate,
    db: Session = Depends(get_db),
) -> AppSetting:
    setting = get_by_key(db, key)
    apply_updates(setting, payload)
    commit_or_400(db, "Could not update setting")
    db.refresh(setting)
    return setting


@router.delete("/{key}", response_model=AppSettingRead)
def delete_setting(key: str, db: Session = Depends(get_db)) -> AppSetting:
    setting = get_by_key(db, key)
    db.delete(setting)
    commit_or_400(db, "Could not delete setting")
    return setting

