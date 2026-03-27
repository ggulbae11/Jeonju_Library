from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.core.database import fetch_all, fetch_one, get_connection
from backend.core.dependencies import get_current_admin_user, get_current_user
from backend.schemas.book import BookCreate, BookListResponse, BookResponse, BookUpdate
from backend.schemas.common import MessageResponse
from backend.services.import_service import normalize_text

router = APIRouter(prefix="/books", tags=["books"])



def _book_by_id(connection, book_id: int) -> dict | None:
    return fetch_one(
        connection,
        """
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
        WHERE b.id = ?
        """,
        (book_id,),
    )


@router.get("", response_model=BookListResponse)
def list_books(
    search: str | None = Query(default=None, description="도서명 또는 저자 검색"),
    library_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(get_current_user),
) -> BookListResponse:
    conditions = ["1 = 1"]
    params: list = []

    if search:
        keyword = normalize_text(search)
        conditions.append("(b.title_normalized LIKE ? OR b.author_normalized LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    if library_id:
        conditions.append("b.library_id = ?")
        params.append(library_id)

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
            ORDER BY b.updated_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple([*params, limit, offset]),
        )

    return BookListResponse(
        total=total_row["count"] if total_row else 0,
        items=[BookResponse(**row) for row in rows],
    )


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, _: dict = Depends(get_current_user)) -> BookResponse:
    with get_connection() as connection:
        book = _book_by_id(connection, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="도서를 찾을 수 없습니다.")
    return BookResponse(**book)


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, _: dict = Depends(get_current_admin_user)) -> BookResponse:
    with get_connection() as connection:
        library = fetch_one(connection, "SELECT id FROM libraries WHERE id = ?", (payload.library_id,))
        if not library:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효한 도서관이 아닙니다.")

        try:
            cursor = connection.execute(
                """
                INSERT INTO books (
                    registration_number,
                    title,
                    author,
                    call_number,
                    room_name,
                    library_id,
                    title_normalized,
                    author_normalized,
                    is_available,
                    source_file
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual')
                """,
                (
                    payload.registration_number.strip(),
                    payload.title.strip(),
                    payload.author.strip(),
                    payload.call_number.strip(),
                    payload.room_name.strip(),
                    payload.library_id,
                    normalize_text(payload.title),
                    normalize_text(payload.author),
                    int(payload.is_available),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 등록번호입니다.",
            ) from exc

        book = _book_by_id(connection, cursor.lastrowid)
    return BookResponse(**book)


@router.put("/{book_id}", response_model=BookResponse)
def update_book(book_id: int, payload: BookUpdate, _: dict = Depends(get_current_admin_user)) -> BookResponse:
    with get_connection() as connection:
        library = fetch_one(connection, "SELECT id FROM libraries WHERE id = ?", (payload.library_id,))
        if not library:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="유효한 도서관이 아닙니다.")

        cursor = connection.execute(
            """
            UPDATE books
            SET registration_number = ?, title = ?, author = ?, call_number = ?, room_name = ?, library_id = ?,
                title_normalized = ?, author_normalized = ?, is_available = ?
            WHERE id = ?
            """,
            (
                payload.registration_number.strip(),
                payload.title.strip(),
                payload.author.strip(),
                payload.call_number.strip(),
                payload.room_name.strip(),
                payload.library_id,
                normalize_text(payload.title),
                normalize_text(payload.author),
                int(payload.is_available),
                book_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="도서를 찾을 수 없습니다.")

        book = _book_by_id(connection, book_id)
    return BookResponse(**book)


@router.delete("/{book_id}", response_model=MessageResponse)
def delete_book(book_id: int, _: dict = Depends(get_current_admin_user)) -> MessageResponse:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="도서를 찾을 수 없습니다.")
    return MessageResponse(message="도서가 삭제되었습니다.")



