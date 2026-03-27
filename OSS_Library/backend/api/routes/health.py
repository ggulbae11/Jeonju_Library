from __future__ import annotations

from fastapi import APIRouter

from backend.core.database import fetch_one, get_connection
from backend.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    with get_connection() as connection:
        book_count = fetch_one(connection, "SELECT COUNT(*) AS count FROM books")

    return HealthResponse(
        status="ok",
        service="backend",
        database_ready=bool(book_count),
    )
