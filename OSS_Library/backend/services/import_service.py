from __future__ import annotations

import re
import threading
from pathlib import Path

import pandas as pd

from backend.core.config import get_settings
from backend.core.database import fetch_all, fetch_one, get_connection, initialize_database
from backend.core.seed_data import LIBRARY_SEEDS, LibrarySeed
from backend.services.user_service import seed_users_from_csv

IMPORT_LOCK = threading.Lock()

CSV_COLUMNS = {
    "도서관명": "library_name",
    "등록번호": "registration_number",
    "서명": "title",
    "저자명": "author",
    "청구기호": "call_number",
    "자료실": "room_name",
}



def normalize_text(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    return cleaned



def _fallback_seed(name: str, index: int) -> LibrarySeed:
    lat = 35.8242 + ((index % 4) - 1.5) * 0.01
    lon = 127.1480 + ((index // 4) - 1.5) * 0.01
    return LibrarySeed(
        code=f"LIB{index + 1:03d}",
        name=name,
        district="전주시",
        address="전북특별자치도 전주시",
        latitude=round(lat, 6),
        longitude=round(lon, 6),
        homepage_url="",
        image_url="",
    )



def seed_libraries(library_names: list[str]) -> None:
    unique_names = sorted({name.strip() for name in library_names if name and name.strip()})
    with get_connection() as connection:
        seed_index = 0
        for name in unique_names:
            seed = LIBRARY_SEEDS.get(name)
            if seed is None:
                seed = _fallback_seed(name, seed_index)
                seed_index += 1
            connection.execute(
                """
                INSERT INTO libraries (code, name, district, address, homepage_url, image_url, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    code = excluded.code,
                    district = excluded.district,
                    address = excluded.address,
                    homepage_url = excluded.homepage_url,
                    image_url = CASE
                        WHEN excluded.image_url <> '' THEN excluded.image_url
                        ELSE libraries.image_url
                    END,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    seed.code,
                    seed.name,
                    seed.district,
                    seed.address,
                    seed.homepage_url,
                    seed.image_url,
                    seed.latitude,
                    seed.longitude,
                ),
            )



def get_library_id_map() -> dict[str, int]:
    with get_connection() as connection:
        rows = fetch_all(connection, "SELECT id, name FROM libraries ORDER BY name")
    return {row["name"]: row["id"] for row in rows}



def get_latest_import_job() -> dict | None:
    with get_connection() as connection:
        return fetch_one(
            connection,
            """
            SELECT id, source_file, status, total_rows, imported_rows, error_message, started_at, finished_at
            FROM import_jobs
            ORDER BY id DESC
            LIMIT 1
            """,
        )



def _prepare_import_job(source_file: Path) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO import_jobs (source_file, status, total_rows, imported_rows, error_message, started_at, finished_at)
            VALUES (?, 'running', 0, 0, NULL, CURRENT_TIMESTAMP, NULL)
            ON CONFLICT(source_file) DO UPDATE SET
                status = 'running',
                total_rows = 0,
                imported_rows = 0,
                error_message = NULL,
                started_at = CURRENT_TIMESTAMP,
                finished_at = NULL
            """,
            (str(source_file),),
        )



def _finish_import_job(source_file: Path, status: str, total_rows: int, imported_rows: int, error_message: str | None = None) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE import_jobs
            SET status = ?, total_rows = ?, imported_rows = ?, error_message = ?, finished_at = CURRENT_TIMESTAMP
            WHERE source_file = ?
            """,
            (status, total_rows, imported_rows, error_message, str(source_file)),
        )



def import_books_from_csv(force: bool = False) -> dict:
    settings = get_settings()
    source_file = settings.booklist_file
    if not source_file.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {source_file}")

    if not IMPORT_LOCK.acquire(blocking=False):
        return {
            "status": "running",
            "message": "이미 CSV 적재 작업이 진행 중입니다.",
            "total_rows": 0,
            "imported_rows": 0,
        }

    total_rows = 0
    imported_rows = 0
    try:
        initialize_database()
        _prepare_import_job(source_file)
        seed_libraries(list(LIBRARY_SEEDS.keys()))

        preview = pd.read_csv(
            source_file,
            encoding="cp949",
            usecols=list(CSV_COLUMNS.keys()),
            dtype=str,
            nrows=5000,
        )
        seed_libraries(preview["도서관명"].fillna("").tolist())
        library_id_map = get_library_id_map()

        with get_connection() as connection:
            if force:
                connection.execute("DELETE FROM books")

        for chunk in pd.read_csv(
            source_file,
            encoding="cp949",
            usecols=list(CSV_COLUMNS.keys()),
            dtype=str,
            chunksize=settings.import_chunk_size,
        ):
            renamed = chunk.rename(columns=CSV_COLUMNS).fillna("")
            renamed = renamed.applymap(lambda value: str(value).strip())
            seed_libraries(renamed["library_name"].tolist())
            library_id_map = get_library_id_map()

            records: list[tuple] = []
            for row in renamed.to_dict(orient="records"):
                library_name = row["library_name"].strip()
                library_id = library_id_map.get(library_name)
                if not library_id:
                    continue

                title = row["title"].strip() or "제목 미상"
                author = row["author"].strip() or "저자 미상"
                call_number = row["call_number"].strip()
                room_name = row["room_name"].strip() or "자료실 정보 없음"
                registration_number = row["registration_number"].strip()
                if not registration_number:
                    continue

                records.append(
                    (
                        registration_number,
                        title,
                        author,
                        call_number,
                        room_name,
                        library_id,
                        normalize_text(title),
                        normalize_text(author),
                        source_file.name,
                    )
                )

            total_rows += len(renamed.index)
            imported_rows += len(records)

            if not records:
                continue

            with get_connection() as connection:
                connection.executemany(
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
                        source_file
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(registration_number) DO UPDATE SET
                        title = excluded.title,
                        author = excluded.author,
                        call_number = excluded.call_number,
                        room_name = excluded.room_name,
                        library_id = excluded.library_id,
                        title_normalized = excluded.title_normalized,
                        author_normalized = excluded.author_normalized,
                        is_available = 1,
                        source_file = excluded.source_file,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    records,
                )

        _finish_import_job(source_file, "completed", total_rows, imported_rows)
        return {
            "status": "completed",
            "message": "CSV 적재가 완료되었습니다.",
            "total_rows": total_rows,
            "imported_rows": imported_rows,
        }
    except Exception as exc:
        _finish_import_job(source_file, "failed", total_rows, imported_rows, str(exc))
        raise
    finally:
        IMPORT_LOCK.release()



def bootstrap_database() -> None:
    settings = get_settings()
    initialize_database()
    seed_users_from_csv()
    seed_libraries(list(LIBRARY_SEEDS.keys()))
    if not settings.booklist_file.exists():
        return

    with get_connection() as connection:
        book_count = fetch_one(connection, "SELECT COUNT(*) AS count FROM books")

    if settings.auto_import_books and book_count and book_count["count"] == 0:
        import_books_from_csv(force=False)



