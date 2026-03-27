from __future__ import annotations

import csv
from pathlib import Path

from backend.core.config import get_settings
from backend.core.database import fetch_one, get_connection
from backend.core.security import hash_password

USER_CSV_COLUMNS = ["username", "password", "email", "full_name", "role", "is_active"]
USER_CSV_ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
DEFAULT_ADMIN_ROW = {
    "username": "admin123",
    "password": "pw123",
    "email": "admin@example.com",
    "full_name": "admin",
    "role": "admin",
    "is_active": "1",
}


def _user_csv_path() -> Path:
    return get_settings().user_csv_file


def ensure_user_csv_exists() -> Path:
    csv_path = _user_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=USER_CSV_COLUMNS)
            writer.writeheader()
            writer.writerow(DEFAULT_ADMIN_ROW)
    return csv_path


def _read_user_rows() -> list[dict[str, str]]:
    csv_path = ensure_user_csv_exists()
    last_error: Exception | None = None
    for encoding in USER_CSV_ENCODINGS:
        try:
            with csv_path.open("r", encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                return [
                    {
                        column: str((row or {}).get(column, "") or "").strip()
                        for column in USER_CSV_COLUMNS
                    }
                    for row in reader
                ]
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    return []


def seed_users_from_csv() -> None:
    rows = _read_user_rows()
    if not rows:
        rows = [DEFAULT_ADMIN_ROW]

    with get_connection() as connection:
        for row in rows:
            username = row["username"].strip()
            password = row["password"].strip()
            email = row["email"].strip()
            full_name = row["full_name"].strip() or None
            role = row["role"].strip() or "user"
            is_active = 0 if row["is_active"].strip() in {"0", "false", "False"} else 1

            if not username or not password or not email:
                continue

            password_hash = hash_password(password)
            existing_user = fetch_one(connection, "SELECT id FROM users WHERE username = ?", (username,))
            if existing_user:
                connection.execute(
                    """
                    UPDATE users
                    SET email = ?, full_name = ?, password_hash = ?, role = ?, is_active = ?
                    WHERE username = ?
                    """,
                    (email, full_name, password_hash, role, is_active, username),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO users (username, email, full_name, password_hash, role, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (username, email, full_name, password_hash, role, is_active),
                )


def append_user_to_csv(
    *,
    username: str,
    password: str,
    email: str,
    full_name: str | None,
    role: str = "user",
    is_active: bool = True,
) -> None:
    csv_path = ensure_user_csv_exists()
    rows = _read_user_rows()
    for row in rows:
        if row["username"].strip() == username.strip() or row["email"].strip() == email.strip():
            return

    with csv_path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=USER_CSV_COLUMNS)
        writer.writerow(
            {
                "username": username.strip(),
                "password": password,
                "email": email.strip(),
                "full_name": (full_name or "").strip(),
                "role": role.strip() or "user",
                "is_active": "1" if is_active else "0",
            }
        )
