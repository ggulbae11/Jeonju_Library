from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.database import fetch_all, fetch_one, get_connection
from backend.core.dependencies import get_current_admin_user, get_current_user
from backend.core.security import create_access_token, hash_password, verify_password
from backend.schemas.auth import TokenResponse, UserCreate, UserListResponse, UserLogin, UserResponse
from backend.services.user_service import append_user_to_csv

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate) -> TokenResponse:
    with get_connection() as connection:
        existing_user = fetch_one(
            connection,
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (payload.username.strip(), payload.email),
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 사용 중인 사용자명 또는 이메일입니다.",
            )

        role = "user"
        password_hash = hash_password(payload.password)
        try:
            cursor = connection.execute(
                """
                INSERT INTO users (username, email, full_name, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.username.strip(),
                    payload.email,
                    payload.full_name.strip() if payload.full_name else None,
                    password_hash,
                    role,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="사용자 생성에 실패했습니다.",
            ) from exc

        user = fetch_one(
            connection,
            """
            SELECT id, username, email, full_name, role, is_active, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        )

    append_user_to_csv(
        username=payload.username,
        password=payload.password,
        email=payload.email,
        full_name=payload.full_name,
        role=user["role"],
        is_active=bool(user["is_active"]),
    )
    access_token = create_access_token(user["username"], user["role"])
    return TokenResponse(access_token=access_token, user=UserResponse(**user))


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin) -> TokenResponse:
    with get_connection() as connection:
        user_record = fetch_one(
            connection,
            """
            SELECT id, username, email, full_name, role, is_active, created_at, updated_at, password_hash
            FROM users
            WHERE username = ?
            """,
            (payload.username.strip(),),
        )

    if not user_record or not verify_password(payload.password, user_record["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user_record["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )

    user = {key: value for key, value in user_record.items() if key != "password_hash"}
    access_token = create_access_token(user["username"], user["role"])
    return TokenResponse(access_token=access_token, user=UserResponse(**user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**current_user)


@router.get("/users", response_model=UserListResponse)
def list_users(_: dict = Depends(get_current_admin_user)) -> UserListResponse:
    with get_connection() as connection:
        rows = fetch_all(
            connection,
            """
            SELECT id, username, email, full_name, role, is_active, created_at, updated_at
            FROM users
            ORDER BY created_at DESC, id DESC
            """,
        )
    return UserListResponse(items=[UserResponse(**row) for row in rows])
