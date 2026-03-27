from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from backend.core.config import get_settings

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE CHECK (length(trim(username)) >= 3),
    email TEXT NOT NULL UNIQUE CHECK (instr(email, '@') > 1),
    full_name TEXT,
    password_hash TEXT NOT NULL CHECK (length(password_hash) >= 32),
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE CHECK (length(trim(code)) >= 2),
    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) >= 2),
    district TEXT NOT NULL DEFAULT '전주시',
    address TEXT NOT NULL DEFAULT '전북특별자치도 전주시',
    homepage_url TEXT NOT NULL DEFAULT '',
    image_url TEXT NOT NULL DEFAULT '',
    latitude REAL NOT NULL CHECK (latitude BETWEEN 33.0 AND 39.5),
    longitude REAL NOT NULL CHECK (longitude BETWEEN 124.0 AND 132.0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_number TEXT NOT NULL UNIQUE CHECK (length(trim(registration_number)) >= 5),
    title TEXT NOT NULL CHECK (length(trim(title)) >= 1),
    author TEXT NOT NULL DEFAULT '저자 미상',
    call_number TEXT NOT NULL DEFAULT '',
    room_name TEXT NOT NULL DEFAULT '자료실 정보 없음',
    library_id INTEGER NOT NULL,
    title_normalized TEXT NOT NULL,
    author_normalized TEXT NOT NULL,
    is_available INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0, 1)),
    source_file TEXT NOT NULL DEFAULT 'booklist.csv',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (library_id) REFERENCES libraries(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS import_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    total_rows INTEGER NOT NULL DEFAULT 0 CHECK (total_rows >= 0),
    imported_rows INTEGER NOT NULL DEFAULT 0 CHECK (imported_rows >= 0),
    error_message TEXT,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_books_library_id ON books (library_id);
CREATE INDEX IF NOT EXISTS idx_books_room_name ON books (room_name);
CREATE INDEX IF NOT EXISTS idx_books_title_normalized ON books (title_normalized);
CREATE INDEX IF NOT EXISTS idx_books_author_normalized ON books (author_normalized);
CREATE INDEX IF NOT EXISTS idx_libraries_name ON libraries (name);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

CREATE TRIGGER IF NOT EXISTS trg_users_updated_at
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_libraries_updated_at
AFTER UPDATE ON libraries
FOR EACH ROW
BEGIN
    UPDATE libraries SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_books_updated_at
AFTER UPDATE ON books
FOR EACH ROW
BEGIN
    UPDATE books SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;
"""



def _connect() -> sqlite3.Connection:
    settings = get_settings()
    settings.database_file.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_file, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA journal_mode = WAL;")
    connection.execute("PRAGMA synchronous = NORMAL;")
    return connection


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()



def ensure_library_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(libraries)").fetchall()
    }
    if "homepage_url" not in columns:
        connection.execute("ALTER TABLE libraries ADD COLUMN homepage_url TEXT NOT NULL DEFAULT ''")
    if "image_url" not in columns:
        connection.execute("ALTER TABLE libraries ADD COLUMN image_url TEXT NOT NULL DEFAULT ''")



def initialize_database() -> None:
    with get_connection() as connection:
        connection.executescript(SCHEMA_SQL)
        ensure_library_columns(connection)



def fetch_one(connection: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    row = connection.execute(query, params).fetchone()
    return dict(row) if row else None



def fetch_all(connection: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]
