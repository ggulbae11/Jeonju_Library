from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.database import fetch_all, fetch_one, get_connection
from backend.core.dependencies import get_current_admin_user, get_current_user
from backend.schemas.book import BookListResponse, BookResponse
from backend.schemas.common import MessageResponse
from backend.schemas.library import LibraryCreate, LibraryMapPoint, LibraryResponse, LibraryUpdate
from backend.services.import_service import normalize_text

router = APIRouter(prefix="/libraries", tags=["libraries"])


@router.get("", response_model=list[LibraryResponse])
def list_libraries(
    search: str | None = Query(default=None, description="도서관명 검색"),
    district: str | None = Query(default=None, description="구 단위 필터"),
) -> list[LibraryResponse]:
    query = """
    SELECT l.*, COUNT(b.id) AS book_count
    FROM libraries l
    LEFT JOIN books b ON b.library_id = l.id
    """
    conditions: list[str] = []
    params: list = []

    if search:
        conditions.append("lower(l.name) LIKE ?")
        params.append(f"%{normalize_text(search)}%")
    if district:
        conditions.append("l.district = ?")
        params.append(district.strip())

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY l.id ORDER BY l.name"

    with get_connection() as connection:
        libraries = fetch_all(connection, query, tuple(params))
    return [LibraryResponse(**library) for library in libraries]


@router.get("/map", response_model=list[LibraryMapPoint])
def library_map_points() -> list[LibraryMapPoint]:
    with get_connection() as connection:
        rows = fetch_all(
            connection,
            """
            SELECT
                l.id,
                l.name,
                l.district,
                l.address,
                l.latitude,
                l.longitude,
                COUNT(b.id) AS book_count
            FROM libraries l
            LEFT JOIN books b ON b.library_id = l.id
            GROUP BY l.id
            ORDER BY l.name
            """,
        )
    return [LibraryMapPoint(**row) for row in rows]


@router.get("/{library_id}", response_model=LibraryResponse)
def get_library(library_id: int) -> LibraryResponse:
    with get_connection() as connection:
        library = fetch_one(
            connection,
            """
            SELECT l.*, COUNT(b.id) AS book_count
            FROM libraries l
            LEFT JOIN books b ON b.library_id = l.id
            WHERE l.id = ?
            GROUP BY l.id
            """,
            (library_id,),
        )
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="도서관을 찾을 수 없습니다.")
    return LibraryResponse(**library)


@router.get("/{library_id}/books", response_model=BookListResponse)
def list_library_books(
    library_id: int,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(get_current_user),
) -> BookListResponse:
    conditions = ["b.library_id = ?"]
    params: list = [library_id]

    if search:
        keyword = normalize_text(search)
        conditions.append("(b.title_normalized LIKE ? OR b.author_normalized LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    where_clause = " AND ".join(conditions)

    with get_connection() as connection:
        total_row = fetch_one(
            connection,
            f"SELECT COUNT(*) AS count FROM books b WHERE {where_clause}",
            tuple(params),
        )
        rows = fetch_all(
            connection,
            f"""
            SELECT
                b.id,
                b.registration_number,
                b.title,
                b.author,
                b.call_number,
                b.room_name,
                b.library_id,
                b.is_available,
                b.created_at,
                b.updated_at,
                l.name AS library_name
            FROM books b
            JOIN libraries l ON l.id = b.library_id
            WHERE {where_clause}
            ORDER BY b.title
            LIMIT ? OFFSET ?
            """,
            tuple([*params, limit, offset]),
        )

    return BookListResponse(
        total=total_row["count"] if total_row else 0,
        items=[BookResponse(**row) for row in rows],
    )


@router.post("", response_model=LibraryResponse, status_code=status.HTTP_201_CREATED)
def create_library(payload: LibraryCreate, _: dict = Depends(get_current_admin_user)) -> LibraryResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO libraries (code, name, district, address, homepage_url, image_url, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.code.strip(),
                payload.name.strip(),
                payload.district.strip(),
                payload.address.strip(),
                payload.homepage_url.strip(),
                payload.image_url.strip(),
                payload.latitude,
                payload.longitude,
            ),
        )
        library = fetch_one(
            connection,
            """
            SELECT l.*, 0 AS book_count
            FROM libraries l
            WHERE l.id = ?
            """,
            (cursor.lastrowid,),
        )
    return LibraryResponse(**library)


@router.put("/{library_id}", response_model=LibraryResponse)
def update_library(
    library_id: int,
    payload: LibraryUpdate,
    _: dict = Depends(get_current_admin_user),
) -> LibraryResponse:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE libraries
            SET code = ?, name = ?, district = ?, address = ?, homepage_url = ?, image_url = ?, latitude = ?, longitude = ?
            WHERE id = ?
            """,
            (
                payload.code.strip(),
                payload.name.strip(),
                payload.district.strip(),
                payload.address.strip(),
                payload.homepage_url.strip(),
                payload.image_url.strip(),
                payload.latitude,
                payload.longitude,
                library_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="도서관을 찾을 수 없습니다.")

        library = fetch_one(
            connection,
            """
            SELECT l.*, COUNT(b.id) AS book_count
            FROM libraries l
            LEFT JOIN books b ON b.library_id = l.id
            WHERE l.id = ?
            GROUP BY l.id
            """,
            (library_id,),
        )
    return LibraryResponse(**library)


@router.delete("/{library_id}", response_model=MessageResponse)
def delete_library(library_id: int, _: dict = Depends(get_current_admin_user)) -> MessageResponse:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM libraries WHERE id = ?", (library_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="도서관을 찾을 수 없습니다.")
    return MessageResponse(message="도서관이 삭제되었습니다.")



