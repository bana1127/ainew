from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import BudgetCategory, BudgetPlan
from app.schemas.budget import (
    BudgetCategoryCreate,
    BudgetCategoryRead,
    BudgetCategoryUpdate,
    BudgetPlanCreate,
    BudgetPlanRead,
    BudgetPlanUpdate,
    TransactionClassifyPayload,
)
from app.services.budget_review_service import (
    confirm_transaction_classification,
    get_review_items,
    preview_transaction_classification,
    resolve_review_item,
)
from app.services.budget_service import (
    ensure_default_categories,
    get_activity_settlements,
    get_budget_cashflow,
    get_budget_summary,
    get_budget_vs_actual,
    parse_date_filter,
    upsert_budget_plan,
)
from app.services.quarter_service import parse_operating_quarter, quarter_date_range_from_str


router = APIRouter()


def _dates(start_date: str | None, end_date: str | None):
    try:
        return parse_date_filter(start_date), parse_date_filter(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date filter: {exc}")


@router.get("/summary")
def budget_summary(
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    operating_quarter: str | None = Query(default=None, description="운영 분기 (예: 2026-Q2)"),
    db: Session = Depends(get_db),
) -> dict:
    start, end = _dates(start_date, end_date)
    if operating_quarter:
        try:
            parse_operating_quarter(operating_quarter)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return get_budget_summary(
        db,
        period=period,
        start_date=start,
        end_date=end,
        operating_quarter=operating_quarter,
    )


@router.get("/cashflow")
def budget_cashflow(
    start_date: str | None = None,
    end_date: str | None = None,
    operating_quarter: str | None = Query(default=None, description="운영 분기 (예: 2026-Q2)"),
    db: Session = Depends(get_db),
) -> list[dict]:
    start, end = _dates(start_date, end_date)
    if operating_quarter:
        try:
            start, end = quarter_date_range_from_str(operating_quarter)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return get_budget_cashflow(db, start_date=start, end_date=end)


@router.get("/categories", response_model=list[BudgetCategoryRead])
def list_budget_categories(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[BudgetCategory]:
    ensure_default_categories(db)
    stmt = select(BudgetCategory)
    if not include_inactive:
        stmt = stmt.where(BudgetCategory.is_active.is_(True))
    return list(db.scalars(stmt.order_by(BudgetCategory.type, BudgetCategory.sort_order, BudgetCategory.name)))


@router.post("/categories", response_model=BudgetCategoryRead)
def create_budget_category(
    payload: BudgetCategoryCreate,
    db: Session = Depends(get_db),
) -> BudgetCategory:
    if payload.type not in {"income", "expense"}:
        raise HTTPException(status_code=400, detail="type must be income or expense")
    category = BudgetCategory(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=BudgetCategoryRead)
def update_budget_category(
    category_id: UUID,
    payload: BudgetCategoryUpdate,
    db: Session = Depends(get_db),
) -> BudgetCategory:
    category = db.get(BudgetCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Budget category not found")
    data = payload.model_dump(exclude_unset=True)
    if "type" in data and data["type"] not in {"income", "expense"}:
        raise HTTPException(status_code=400, detail="type must be income or expense")
    for key, value in data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.get("/plans", response_model=list[BudgetPlanRead])
def list_budget_plans(
    period: str | None = None,
    db: Session = Depends(get_db),
) -> list[BudgetPlan]:
    stmt = select(BudgetPlan)
    if period:
        stmt = stmt.where(BudgetPlan.period == period)
    return list(db.scalars(stmt))


@router.post("/plans", response_model=BudgetPlanRead)
def create_budget_plan(
    payload: BudgetPlanCreate,
    db: Session = Depends(get_db),
) -> BudgetPlan:
    if db.get(BudgetCategory, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="Budget category not found")
    return upsert_budget_plan(
        db,
        period=payload.period,
        category_id=payload.category_id,
        planned_amount=payload.planned_amount,
        note=payload.note,
    )


@router.patch("/plans/{plan_id}", response_model=BudgetPlanRead)
def update_budget_plan(
    plan_id: UUID,
    payload: BudgetPlanUpdate,
    db: Session = Depends(get_db),
) -> BudgetPlan:
    plan = db.get(BudgetPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Budget plan not found")
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and db.get(BudgetCategory, data["category_id"]) is None:
        raise HTTPException(status_code=404, detail="Budget category not found")
    for key, value in data.items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/budget-vs-actual")
def budget_vs_actual(
    period: str,
    start_date: str | None = None,
    end_date: str | None = None,
    operating_quarter: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    start, end = _dates(start_date, end_date)
    if operating_quarter:
        try:
            start, end = quarter_date_range_from_str(operating_quarter)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return get_budget_vs_actual(db, period=period, start_date=start, end_date=end)


@router.get("/activity-settlements")
def budget_activity_settlements(
    start_date: str | None = None,
    end_date: str | None = None,
    operating_quarter: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    start, end = _dates(start_date, end_date)
    if operating_quarter:
        try:
            start, end = quarter_date_range_from_str(operating_quarter)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return get_activity_settlements(db, start_date=start, end_date=end)


@router.get("/review-items")
def budget_review_items(
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    operating_quarter: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    start, end = _dates(start_date, end_date)
    if operating_quarter:
        try:
            start, end = quarter_date_range_from_str(operating_quarter)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    return get_review_items(db, period=period, start_date=start, end_date=end)


@router.get("/quarter-summary")
def budget_quarter_summary(
    operating_quarter: str = Query(..., description="운영 분기 (예: 2026-Q2)"),
    db: Session = Depends(get_db),
) -> dict:
    """분기별 예산 요약 (수입/지출/제외 내역 포함)."""
    try:
        q_start, q_end = quarter_date_range_from_str(operating_quarter)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return get_budget_summary(
        db,
        start_date=q_start,
        end_date=q_end,
        operating_quarter=operating_quarter,
    )


@router.post("/review-items/{item_id}/resolve")
def resolve_budget_review_item(
    item_id: str,
    payload: dict | None = None,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return resolve_review_item(db, item_id=item_id, note=(payload or {}).get("note"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/transactions/{transaction_id}/classify-preview")
def budget_transaction_classify_preview(
    transaction_id: UUID,
    payload: TransactionClassifyPayload,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return preview_transaction_classification(
            db,
            transaction_id=transaction_id,
            payload=payload.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/transactions/classify-confirm")
def budget_transaction_classify_confirm(
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return confirm_transaction_classification(db, action_id=UUID(str(payload["action_id"])))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/transactions/{transaction_id}/classify-confirm")
def budget_transaction_classify_confirm_for_transaction(
    transaction_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
) -> dict:
    # transaction_id is kept for API ergonomics; action_id still drives safe confirmation.
    return budget_transaction_classify_confirm(payload, db)


# ── Task 43: Quarter export endpoints ─────────────────────────────────────────

from fastapi.responses import Response, StreamingResponse


@router.get("/quarter-export/csv")
def export_quarter_csv(
    operating_quarter: str = Query(..., description="운영 분기 (예: 2026-Q2)"),
    db: Session = Depends(get_db),
) -> Response:
    """분기 거래내역 CSV 다운로드."""
    try:
        parse_operating_quarter(operating_quarter)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    from app.services.budget_export_service import (
        get_quarter_transactions,
        build_transaction_csv,
        get_quarter_receipts,
        build_receipt_csv,
    )
    import io, zipfile

    txs = get_quarter_transactions(db, operating_quarter)
    receipts = get_quarter_receipts(db, operating_quarter)

    # Combined CSV
    tx_csv = build_transaction_csv(txs)
    receipt_csv = build_receipt_csv(receipts)
    combined = f"# 거래내역 ({operating_quarter})\n{tx_csv}\n\n# 증빙 목록 ({operating_quarter})\n{receipt_csv}"

    return Response(
        content=combined.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename={operating_quarter}_budget.csv",
        },
    )


@router.get("/quarter-export/zip")
def export_quarter_zip(
    operating_quarter: str = Query(..., description="운영 분기 (예: 2026-Q2)"),
    db: Session = Depends(get_db),
) -> Response:
    """분기 증빙 ZIP 다운로드 (거래내역 CSV + 증빙 파일 포함)."""
    try:
        parse_operating_quarter(operating_quarter)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    from app.core.config import settings
    from app.services.budget_export_service import build_quarter_zip

    try:
        zip_bytes = build_quarter_zip(db, operating_quarter, settings.UPLOAD_DIR)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ZIP 생성 실패: {exc}")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={operating_quarter}_evidence.zip",
        },
    )
