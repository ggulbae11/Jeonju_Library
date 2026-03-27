from __future__ import annotations

from pydantic import BaseModel


class ImportJobResponse(BaseModel):
    id: int | None = None
    source_file: str | None = None
    status: str
    total_rows: int = 0
    imported_rows: int = 0
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    message: str | None = None
