from __future__ import annotations

from pydantic import BaseModel, Field


class BookBase(BaseModel):
    registration_number: str = Field(min_length=5, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    call_number: str = Field(default="", max_length=100)
    room_name: str = Field(default="자료실 정보 없음", max_length=100)
    library_id: int = Field(gt=0)
    is_available: bool = True


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    pass


class BookResponse(BookBase):
    id: int
    library_name: str
    created_at: str
    updated_at: str


class BookListResponse(BaseModel):
    total: int
    items: list[BookResponse]
