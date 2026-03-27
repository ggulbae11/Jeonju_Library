from __future__ import annotations

from pydantic import BaseModel, Field


class LibraryBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    district: str = Field(min_length=2, max_length=50)
    address: str = Field(min_length=2, max_length=255)
    homepage_url: str = Field(default="", max_length=500)
    image_url: str = Field(default="", max_length=1000)
    latitude: float = Field(ge=33.0, le=39.5)
    longitude: float = Field(ge=124.0, le=132.0)


class LibraryCreate(LibraryBase):
    code: str = Field(min_length=2, max_length=30)


class LibraryUpdate(LibraryBase):
    code: str = Field(min_length=2, max_length=30)


class LibraryResponse(LibraryCreate):
    id: int
    created_at: str
    updated_at: str
    book_count: int = 0


class LibraryMapPoint(BaseModel):
    id: int
    name: str
    district: str
    address: str
    latitude: float
    longitude: float
    book_count: int
