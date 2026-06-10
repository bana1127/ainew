from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import N8nStatusRead, N8nTestPayload, N8nTestResult
from app.services import n8n_service
from app.services.n8n_service import N8nServiceError

router = APIRouter()


@router.get("/n8n/status", response_model=N8nStatusRead)
def get_n8n_status() -> dict:
    return n8n_service.get_n8n_status()


@router.post("/n8n/test", response_model=N8nTestResult)
def send_n8n_test(payload: N8nTestPayload) -> N8nTestResult:
    try:
        n8n_service.send_test_email(payload.model_dump())
    except N8nServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return N8nTestResult(ok=True, status="success", detail="n8n test webhook sent")
