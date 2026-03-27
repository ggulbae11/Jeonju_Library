from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.dependencies import get_current_admin_user
from backend.schemas.import_job import ImportJobResponse
from backend.services.import_service import get_latest_import_job, import_books_from_csv

router = APIRouter(prefix="/imports", tags=["imports"])


@router.get("/latest", response_model=ImportJobResponse)
def latest_import_job() -> ImportJobResponse:
    job = get_latest_import_job()
    if not job:
        return ImportJobResponse(status="pending", message="아직 적재 이력이 없습니다.")
    return ImportJobResponse(**job)


@router.post("/booklist", response_model=ImportJobResponse, status_code=status.HTTP_202_ACCEPTED)
def run_book_import(
    force: bool = Query(default=False, description="기존 도서 데이터를 비우고 다시 적재합니다."),
    _: dict = Depends(get_current_admin_user),
) -> ImportJobResponse:
    try:
        result = import_books_from_csv(force=force)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    job = get_latest_import_job()
    if job:
        merged = {**job, **result}
        return ImportJobResponse(**merged)
    return ImportJobResponse(**result)
