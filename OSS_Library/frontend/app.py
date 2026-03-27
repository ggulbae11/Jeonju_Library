from __future__ import annotations

import math
import os
import re
from html import escape
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
DEFAULT_HEADERS = {"Content-Type": "application/json"}
PAGE_SIZE = 12


def api_request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> requests.Response:
    headers = DEFAULT_HEADERS.copy()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return requests.request(
        method=method,
        url=f"{BACKEND_BASE_URL}{path}",
        headers=headers,
        params=params,
        json=json,
        timeout=60,
    )


def ensure_session_state() -> None:
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("selected_library_id", None)
    st.session_state.setdefault("selected_district", "전체")
    st.session_state.setdefault("global_page", 1)
    st.session_state.setdefault("library_page", 1)
    st.session_state.setdefault("last_global_signature", "")
    st.session_state.setdefault("last_library_signature", "")
    st.session_state.setdefault("library_detail_search", "")
    st.session_state.setdefault("pending_library_detail_search", None)
    st.session_state.setdefault("show_admin_users", False)


@st.cache_data(ttl=120)
def load_libraries(district: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    if district and district != "전체":
        params["district"] = district
    response = api_request("GET", f"{API_PREFIX}/libraries", params=params)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=120)
def load_all_libraries() -> list[dict[str, Any]]:
    response = api_request("GET", f"{API_PREFIX}/libraries")
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=120)
def search_books(search: str, library_id: int | None, page: int, page_size: int, token: str | None) -> tuple[int, pd.DataFrame]:
    params: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}
    if search:
        params["search"] = search
    if library_id:
        params["library_id"] = library_id
    response = api_request("GET", f"{API_PREFIX}/books", params=params, token=token)
    response.raise_for_status()
    payload = response.json()
    return payload["total"], pd.DataFrame(payload["items"])


@st.cache_data(ttl=120)
def library_books(library_id: int, search: str, page: int, page_size: int, token: str | None) -> tuple[int, pd.DataFrame]:
    response = api_request(
        "GET",
        f"{API_PREFIX}/libraries/{library_id}/books",
        token=token,
        params={
            "limit": page_size,
            "offset": (page - 1) * page_size,
            "search": search,
        },
    )
    response.raise_for_status()
    payload = response.json()
    return payload["total"], pd.DataFrame(payload["items"])


@st.cache_data(ttl=120)
def latest_import_status() -> dict[str, Any]:
    response = api_request("GET", f"{API_PREFIX}/imports/latest")
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=120)
def load_registered_users(token: str | None) -> pd.DataFrame:
    response = api_request("GET", f"{API_PREFIX}/auth/users", token=token)
    response.raise_for_status()
    payload = response.json()
    return pd.DataFrame(payload["items"])


def primary_author_token(author: str) -> str:
    parts = re.split(r"[;,·/]| 글| 그림| 지음| 옮김| 편저| 저", author)
    for part in parts:
        cleaned = part.strip()
        if len(cleaned) >= 2:
            return cleaned
    return author.strip()


def logout_current_user() -> None:
    st.session_state["token"] = None
    st.session_state["user"] = None
    st.session_state["selected_library_id"] = None
    st.session_state["library_detail_search"] = ""
    st.session_state["pending_library_detail_search"] = None
    st.session_state["show_admin_users"] = False


def build_library_image_url(library: dict[str, Any]) -> str:
    image_url = (library.get("image_url") or "").strip()
    if image_url:
        return image_url

    district = library.get("district", "전주")
    name = library.get("name", "도서관")
    short_name = name.replace("전주시립", "").replace("도서관", "")[:8] or name[:8]
    svg = f"""
    <svg xmlns='http://www.w3.org/2000/svg' width='960' height='540' viewBox='0 0 960 540'>
      <defs>
        <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
          <stop offset='0%' stop-color='#0f4c81'/>
          <stop offset='100%' stop-color='#60a5fa'/>
        </linearGradient>
      </defs>
      <rect width='960' height='540' fill='url(#g)' rx='32'/>
      <text x='72' y='220' fill='white' font-size='34' font-family='Arial, sans-serif' font-weight='700'>{district}</text>
      <text x='72' y='310' fill='white' font-size='62' font-family='Arial, sans-serif' font-weight='900'>{short_name}</text>
      <text x='72' y='375' fill='rgba(255,255,255,0.88)' font-size='24' font-family='Arial, sans-serif'>Jeonju Library</text>
    </svg>
    """
    return f"data:image/svg+xml;charset=utf-8,{quote(svg)}"


def render_library_image(library: dict[str, Any], css_class: str = "library-image-frame") -> None:
    image_url = build_library_image_url(library)
    alt = escape(library.get("name", "도서관 이미지"))
    st.markdown(
        f"<div class='{css_class}'><img src='{escape(image_url, quote=True)}' alt='{alt}'/></div>",
        unsafe_allow_html=True,
    )


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --blue-1: #0f4c81;
            --blue-2: #3b82c4;
            --ink: #0f172a;
            --muted: #475569;
        }
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(59, 130, 196, 0.18), transparent 28%),
                radial-gradient(circle at bottom right, rgba(15, 76, 129, 0.16), transparent 30%),
                linear-gradient(135deg, #f5faff 0%, #edf6ff 48%, #f8fbff 100%);
            color: var(--ink);
        }
        .stApp, .stApp * {
            color: var(--ink) !important;
        }
        .block-container {
            max-width: 1320px;
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 5.5rem;
            padding-right: 5.5rem;
        }
        header[data-testid="stHeader"],
        [data-testid="stToolbar"],
        #MainMenu {
            display: none !important;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--blue-1) 0%, var(--blue-2) 100%);
        }
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] *,
        [data-testid="stSidebarNav"],
        [data-testid="stSidebarNav"] * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stTabs [data-baseweb="tab"] {
            color: #ffffff !important;
        }
        [data-testid="stPopoverButton"] button {
            border-radius: 999px;
            border: 1px solid rgba(15, 76, 129, 0.10);
            background: linear-gradient(135deg, var(--blue-1) 0%, var(--blue-2) 100%) !important;
            color: white !important;
            -webkit-text-fill-color: white !important;
            box-shadow: 0 10px 24px rgba(59, 130, 196, 0.20);
        }
        [data-testid="stPopover"] > div {
            background: linear-gradient(180deg, rgba(15, 76, 129, 0.96) 0%, rgba(59, 130, 196, 0.96) 100%) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            border-radius: 22px !important;
            box-shadow: 0 18px 36px rgba(15, 76, 129, 0.22) !important;
        }
        [data-testid="stPopover"] * {
            color: white !important;
            -webkit-text-fill-color: white !important;
        }
        .stTextInput input,
        .stTextInput input::placeholder,
        .stSelectbox div[data-baseweb="select"] input,
        .stSelectbox div[data-baseweb="select"] p,
        .stSelectbox div[data-baseweb="select"] span,
        .stSelectbox div[data-baseweb="select"] div,
        .stSelectbox [data-baseweb="select"] *[class*="singleValue"],
        .stSelectbox [data-baseweb="select"] *[class*="placeholder"],
        .stSelectbox div[data-baseweb="popover"] *,
        div[role="listbox"] *,
        li[role="option"] *,
        ul[role="listbox"] * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stSelectbox div[data-baseweb="select"] input,
        .stSelectbox div[data-baseweb="popover"] > div,
        div[role="listbox"],
        li[role="option"],
        .stNumberInput input {
            background: linear-gradient(135deg, var(--blue-1) 0%, var(--blue-2) 100%) !important;
            border: 1px solid rgba(255,255,255,0.16) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        .stButton button, .stDownloadButton button {
            border-radius: 999px;
            border: 1px solid rgba(15, 76, 129, 0.10);
            background: linear-gradient(135deg, var(--blue-1) 0%, var(--blue-2) 100%);
            color: white !important;
            -webkit-text-fill-color: white !important;
            font-weight: 700;
            min-height: 2.8rem;
            box-shadow: 0 10px 24px rgba(59, 130, 196, 0.20);
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.62);
            border: 1px solid rgba(255, 255, 255, 0.84);
            box-shadow: 0 22px 50px rgba(15, 76, 129, 0.10);
            backdrop-filter: blur(16px);
            border-radius: 28px;
            padding: 1.3rem 1.45rem;
            margin-bottom: 1.4rem;
        }
        .hero-title {
            font-size: 2.35rem;
            font-weight: 900;
            letter-spacing: -0.03em;
            margin-bottom: 0.3rem;
            color: var(--blue-1) !important;
        }
        .hero-caption {
            font-size: 1rem;
            margin-bottom: 0;
            color: var(--muted) !important;
        }
        .metric-chip {
            padding: 0.9rem 1rem;
            border-radius: 20px;
            background: linear-gradient(135deg, var(--blue-1) 0%, var(--blue-2) 100%);
            border: 1px solid rgba(255, 255, 255, 0.18);
            text-align: center;
            color: white !important;
            box-shadow: 0 12px 26px rgba(59, 130, 196, 0.20);
        }
        .metric-chip * {
            color: white !important;
            -webkit-text-fill-color: white !important;
        }
        .user-pill {
            background: linear-gradient(135deg, var(--blue-1) 0%, var(--blue-2) 100%);
            border-radius: 999px;
            padding: 0.6rem 0.95rem;
            border: 1px solid rgba(255,255,255,0.18);
            box-shadow: 0 10px 22px rgba(59, 130, 196, 0.18);
            margin-top: 0.65rem;
            min-height: auto;
            display: inline-flex;
            flex-direction: row;
            align-items: center;
            justify-content: center;
            gap: 0.45rem;
            white-space: nowrap;
        }
        .user-pill * {
            color: white !important;
            -webkit-text-fill-color: white !important;
        }
        .user-pill-label {
            font-size: 0.74rem;
            opacity: 0.9;
            margin-bottom: 0;
            font-weight: 700;
        }
        .user-pill-name {
            font-size: 0.95rem;
            font-weight: 900;
            line-height: 1.1;
        }
        .library-image-frame {
            width: 100%;
            aspect-ratio: 16 / 9;
            overflow: hidden;
            border-radius: 22px;
            margin-bottom: 0.95rem;
            box-shadow: 0 12px 24px rgba(15, 76, 129, 0.10);
            background: linear-gradient(135deg, rgba(15,76,129,0.14) 0%, rgba(59,130,196,0.20) 100%);
        }
        .library-image-frame img, .library-image-detail img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        .library-image-detail {
            width: 100%;
            aspect-ratio: 16 / 10;
            overflow: hidden;
            border-radius: 24px;
            box-shadow: 0 14px 28px rgba(15, 76, 129, 0.12);
            background: linear-gradient(135deg, rgba(15,76,129,0.14) 0%, rgba(59,130,196,0.20) 100%);
        }
        .result-card {
            background: linear-gradient(180deg, rgba(255,255,255,0.88) 0%, rgba(239,246,255,0.94) 100%);
            border: 1px solid rgba(59, 130, 196, 0.18);
            border-radius: 22px;
            padding: 1.15rem 1.1rem 1rem 1.1rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 14px 30px rgba(15, 76, 129, 0.08);
            min-height: 182px;
        }
        .result-title {
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 0.35rem;
            color: var(--blue-1) !important;
        }
        .result-meta {
            color: var(--muted) !important;
            font-size: 0.93rem;
            line-height: 1.6;
        }
        .result-badge {
            display: inline-block;
            margin-bottom: 0.65rem;
            padding: 0.3rem 0.7rem;
            border-radius: 999px;
            background: linear-gradient(135deg, var(--blue-1) 0%, var(--blue-2) 100%);
            color: white !important;
            -webkit-text-fill-color: white !important;
            font-size: 0.84rem;
            font-weight: 800;
        }
        .filter-active {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(59, 130, 196, 0.12);
            color: var(--blue-1) !important;
            font-weight: 700;
            font-size: 0.9rem;
        }
        .pager-note, .library-filter-note {
            color: var(--muted) !important;
            font-size: 0.92rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_auth_contents(key_prefix: str) -> None:
    token = st.session_state["token"]
    user = st.session_state["user"]

    if token and user:
        st.success(f"{user['username']} 님 로그인됨 ({user['role']})")
        if st.button("로그아웃", key=f"logout-{key_prefix}", use_container_width=True):
            logout_current_user()
            st.rerun()
        return

    login_tab, register_tab = st.tabs(["로그인", "회원가입"])

    with login_tab:
        with st.form(f"login_form_{key_prefix}"):
            username = st.text_input("아이디", key=f"login_username_{key_prefix}")
            password = st.text_input("비밀번호", type="password", key=f"login_password_{key_prefix}")
            submitted = st.form_submit_button("로그인", use_container_width=True)
        if submitted:
            response = api_request("POST", f"{API_PREFIX}/auth/login", json={"username": username, "password": password})
            if response.ok:
                payload = response.json()
                st.session_state["token"] = payload["access_token"]
                st.session_state["user"] = payload["user"]
                st.rerun()
            else:
                st.error(response.json().get("detail", "로그인에 실패했습니다."))

    with register_tab:
        with st.form(f"register_form_{key_prefix}"):
            username = st.text_input("새 아이디", key=f"register_username_{key_prefix}")
            email = st.text_input("이메일", key=f"register_email_{key_prefix}")
            full_name = st.text_input("이름", key=f"register_full_name_{key_prefix}")
            password = st.text_input("새 비밀번호", type="password", key=f"register_password_{key_prefix}")
            submitted = st.form_submit_button("회원가입", use_container_width=True)
        if submitted:
            response = api_request(
                "POST",
                f"{API_PREFIX}/auth/register",
                json={"username": username, "email": email, "full_name": full_name, "password": password},
            )
            if response.ok:
                payload = response.json()
                st.session_state["token"] = payload["access_token"]
                st.session_state["user"] = payload["user"]
                load_registered_users.clear()
                st.rerun()
            else:
                st.error(response.json().get("detail", "회원가입에 실패했습니다."))


def render_auth_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 계정")
        render_auth_contents("sidebar")


def render_account_corner() -> None:
    with st.popover("👤", use_container_width=False):
        st.markdown("### 계정")
        render_auth_contents("popover")


def render_admin_sidebar() -> None:
    user = st.session_state["user"]
    token = st.session_state["token"]
    if not user or user.get("role") != "admin":
        return

    st.sidebar.markdown("## 관리자")
    if st.sidebar.button("CSV 다시 적재", use_container_width=True):
        response = api_request("POST", f"{API_PREFIX}/imports/booklist", token=token, params={"force": False})
        if response.ok:
            load_libraries.clear()
            load_all_libraries.clear()
            search_books.clear()
            library_books.clear()
            latest_import_status.clear()
            load_registered_users.clear()
            st.sidebar.success("CSV 적재 요청을 보냈습니다.")
        else:
            st.sidebar.error(response.json().get("detail", "적재 요청에 실패했습니다."))


def render_admin_users_panel() -> None:
    user = st.session_state.get("user")
    token = st.session_state.get("token")
    if not user or user.get("role") != "admin" or not token:
        return

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    head_left, head_right = st.columns([2.6, 1.4], gap="large")
    with head_left:
        st.subheader("가입 사용자 목록")
        st.caption("admin 계정에서만 전체 사용자 정보를 볼 수 있습니다.")
    with head_right:
        label = "사용자 목록 숨기기" if st.session_state["show_admin_users"] else "사용자 목록 보기"
        if st.button(label, key="toggle-admin-users", use_container_width=True):
            st.session_state["show_admin_users"] = not st.session_state["show_admin_users"]
            st.rerun()

    if st.session_state["show_admin_users"]:
        try:
            users_df = load_registered_users(token)
            if users_df.empty:
                st.info("표시할 사용자가 없습니다.")
            else:
                users_df = users_df.rename(
                    columns={
                        "username": "아이디",
                        "email": "이메일",
                        "full_name": "이름",
                        "role": "권한",
                        "is_active": "활성화",
                        "created_at": "가입일시",
                    }
                )[["아이디", "이메일", "이름", "권한", "활성화", "가입일시"]]
                users_df["활성화"] = users_df["활성화"].map({True: "사용", False: "중지", 1: "사용", 0: "중지"})
                st.dataframe(users_df, use_container_width=True, hide_index=True)
        except requests.RequestException as exc:
            st.error(f"사용자 목록을 불러오지 못했습니다: {exc}")

    st.markdown("</div>", unsafe_allow_html=True)


def render_hero(import_status: dict[str, Any], libraries: list[dict[str, Any]]) -> None:
    current_user = st.session_state.get("user")
    total_books = sum(int(library.get("book_count", 0)) for library in libraries)
    total_libraries = len(libraries)
    status_text = import_status.get("status", "pending")

    hero_left, hero_right = st.columns([4.6, 1.4], gap="large")
    with hero_left:
        st.markdown(
            """
            <div class="glass-card">
                <div class="hero-title">전주 내 도서관 도서 검색</div>
                <p class="hero-caption">
                    전주 도서관 메타데이터와 도서 목록을 함께 연결해, 도서관별 탐색과 도서 검색을 한 화면에서 할 수 있습니다.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hero_right:
        render_account_corner()
        if current_user:
            display_name = current_user.get("full_name") or current_user.get("username")
            st.markdown(
                f"""
                <div class="user-pill"><span class="user-pill-label">로그인 사용자</span><span class="user-pill-name">{display_name}</span></div>
                """,
                unsafe_allow_html=True,
            )

    col1, col2, col3 = st.columns(3, gap="large")
    col1.markdown(f'<div class="metric-chip"><div>도서관 수</div><strong>{total_libraries:,}</strong></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-chip"><div>적재 도서 수</div><strong>{total_books:,}</strong></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-chip"><div>적재 상태</div><strong>{status_text}</strong></div>', unsafe_allow_html=True)


def set_selected_library(library_id: int) -> None:
    st.session_state["selected_library_id"] = library_id
    st.session_state["library_page"] = 1
    st.session_state["last_library_signature"] = ""


def maybe_reset_page(signature: str, page_key: str, signature_key: str) -> None:
    if st.session_state.get(signature_key) != signature:
        st.session_state[page_key] = 1
        st.session_state[signature_key] = signature


def open_same_author_books(book: dict[str, Any]) -> None:
    author_keyword = primary_author_token(book.get("author", "")) or book.get("author", "")
    st.session_state["selected_library_id"] = book["library_id"]
    st.session_state["library_page"] = 1
    st.session_state["last_library_signature"] = ""
    st.session_state["pending_library_detail_search"] = author_keyword


def render_pagination(total: int, page_key: str, page_size: int = PAGE_SIZE) -> None:
    total_pages = max(1, math.ceil(total / page_size))
    current_page = min(st.session_state.get(page_key, 1), total_pages)
    st.session_state[page_key] = current_page

    left, center, right, jump = st.columns([1, 1.2, 1, 1.8], gap="medium")
    with left:
        if st.button("이전", key=f"prev-{page_key}", use_container_width=True, disabled=current_page <= 1):
            st.session_state[page_key] = current_page - 1
            st.rerun()
    with center:
        st.markdown(f"<div class='pager-note' style='text-align:center;'>페이지 {current_page} / {total_pages}</div>", unsafe_allow_html=True)
    with right:
        if st.button("다음", key=f"next-{page_key}", use_container_width=True, disabled=current_page >= total_pages):
            st.session_state[page_key] = current_page + 1
            st.rerun()
    with jump:
        jump_label, jump_input, jump_button = st.columns([1.05, 0.8, 0.9], gap="small")
        with jump_label:
            st.markdown("<div class='pager-note' style='text-align:right; padding-top:0.45rem;'>페이지 이동</div>", unsafe_allow_html=True)
        with jump_input:
            target_page = st.number_input(
                "페이지 이동",
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                label_visibility="collapsed",
                key=f"jump-input-{page_key}",
            )
        with jump_button:
            if st.button("이동", key=f"jump-button-{page_key}", use_container_width=True):
                st.session_state[page_key] = int(target_page)
                st.rerun()


def render_district_filter() -> str:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("구 선택")
    left, center, right = st.columns(3, gap="large")
    options = ["전체", "덕진구", "완산구"]
    for col, option in zip([left, center, right], options):
        with col:
            if st.button(option, use_container_width=True, type="primary" if st.session_state["selected_district"] == option else "secondary"):
                st.session_state["selected_district"] = option
                st.rerun()
    st.markdown(f"<span class='filter-active'>현재 선택: {st.session_state['selected_district']}</span>", unsafe_allow_html=True)
    st.markdown("<div class='library-filter-note'>선택한 구에 해당하는 도서관만 아래 목록에 표시됩니다.</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    return st.session_state["selected_district"]


def render_library_cards(libraries: list[dict[str, Any]]) -> None:
    is_logged_in = bool(st.session_state.get("token"))
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("전주 도서관 목록")
    st.caption("도서관 카드를 보고 원하는 도서관을 선택해 들어갈 수 있습니다.")
    if not is_logged_in:
        st.warning("로그인 후 도서관 입장과 도서 검색을 사용할 수 있습니다.")

    if not libraries:
        st.info("선택한 구에 해당하는 도서관이 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    rows = math.ceil(len(libraries) / 3)
    for row_index in range(rows):
        cols = st.columns(3, gap="large")
        chunk = libraries[row_index * 3 : (row_index + 1) * 3]
        for col, library in zip(cols, chunk):
            with col:
                render_library_image(library)
                st.markdown(
                    f"""
                    <div class="result-card">
                        <div class="result-badge">{library['district']}</div>
                        <div class="result-title">{library['name']}</div>
                        <div class="result-meta">{library['address']}</div>
                        <div class="result-meta">보유 도서 {int(library.get('book_count', 0)):,}권</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("도서관 입장", key=f"library-{library['id']}", use_container_width=True, disabled=not is_logged_in):
                    set_selected_library(library["id"])
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_result_cards(frame: pd.DataFrame, mode: str, action_prefix: str) -> None:
    if frame.empty:
        st.info("조건에 맞는 도서가 없습니다.")
        return

    records = frame.to_dict(orient="records")
    for row_index in range(0, len(records), 2):
        cols = st.columns(2, gap="large")
        pair = records[row_index : row_index + 2]
        for col, row in zip(cols, pair):
            with col:
                badge = row["library_name"] if mode == "global" else row["room_name"]
                meta_lines = [f"저자: {row['author']}"]
                if mode == "global":
                    meta_lines.append(f"소장 도서관: {row['library_name']}")
                meta_lines.append(f"자료실: {row['room_name']}")
                st.markdown(
                    f"""
                    <div class="result-card">
                        <div class="result-badge">{badge}</div>
                        <div class="result-title">{row['title']}</div>
                        <div class="result-meta">{' | '.join(meta_lines)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("같은 저자의 책", key=f"{action_prefix}-author-{row['id']}", use_container_width=True):
                    open_same_author_books(row)
                    st.rerun()


def render_library_detail(libraries: list[dict[str, Any]]) -> None:
    token = st.session_state.get("token")
    pending_search = st.session_state.pop("pending_library_detail_search", None)
    if pending_search is not None:
        st.session_state["library_detail_search"] = pending_search

    selected_library_id = st.session_state.get("selected_library_id")
    selected_library = next((library for library in libraries if library["id"] == selected_library_id), None)
    if not selected_library:
        st.session_state["selected_library_id"] = None
        st.rerun()
        return

    if not token:
        st.warning("도서관 상세와 도서 검색은 로그인 후 이용할 수 있습니다.")
        if st.button("목록으로 돌아가기", key="detail-back-logged-out"):
            st.session_state["selected_library_id"] = None
            st.rerun()
        return

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    top_left, top_right = st.columns([1.15, 1.85], gap="large")
    with top_left:
        render_library_image(selected_library, "library-image-detail")
    with top_right:
        if st.button("목록으로 돌아가기", use_container_width=False):
            st.session_state["selected_library_id"] = None
            st.session_state["library_page"] = 1
            st.session_state["pending_library_detail_search"] = ""
            st.rerun()
        st.subheader(selected_library["name"])
        st.markdown(
            f"**도서관 홈페이지**: [{selected_library['homepage_url']}]({selected_library['homepage_url']})"
            if selected_library.get("homepage_url")
            else "**도서관 홈페이지**: 정보 없음"
        )
        st.markdown(f"**도서관 주소**: {selected_library['address']}")
        st.markdown(f"**구 분류**: {selected_library['district']}")
        st.markdown(f"**보유 도서 수**: {int(selected_library.get('book_count', 0)):,}권")

    st.markdown("---")
    search_value = st.text_input(
        "이 도서관 안에서 도서 검색",
        placeholder="도서명 또는 저자를 입력하세요",
        key="library_detail_search",
    )
    signature = f"{selected_library['id']}::{search_value.strip()}"
    maybe_reset_page(signature, "library_page", "last_library_signature")
    current_page = st.session_state["library_page"]

    total, books_df = library_books(selected_library["id"], search_value, current_page, PAGE_SIZE, token)
    st.write(f"조회 결과: {total:,}권")
    render_result_cards(books_df, mode="library", action_prefix="library")
    if total > 0:
        render_pagination(total, "library_page")
    st.markdown("</div>", unsafe_allow_html=True)


def render_search_section(libraries: list[dict[str, Any]]) -> None:
    token = st.session_state.get("token")
    is_logged_in = bool(token)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("전체 도서 검색")
    if not is_logged_in:
        st.warning("로그인 후 전체 도서 검색을 사용할 수 있습니다.")

    left, right = st.columns([2, 1], gap="large")
    with left:
        search_value = st.text_input("도서명 또는 저자명 검색", placeholder="예: 용선생 세계사", disabled=not is_logged_in)
    with right:
        options = {"전체 도서관": None}
        options.update({library["name"]: library["id"] for library in libraries})
        selected_library_name = st.selectbox("도서관 필터", options=list(options.keys()), disabled=not is_logged_in)
        selected_library_id = options[selected_library_name]

    signature = f"{search_value.strip()}::{selected_library_id}"
    maybe_reset_page(signature, "global_page", "last_global_signature")
    current_page = st.session_state["global_page"]

    if is_logged_in and search_value:
        total, result_df = search_books(search_value, selected_library_id, current_page, PAGE_SIZE, token)
        st.write(f"조회 결과: {total:,}권")
        render_result_cards(result_df, mode="global", action_prefix="global")
        if total > 0:
            render_pagination(total, "global_page")
    else:
        st.caption("도서를 먼저 검색하면 해당 책이 있는 도서관을 바로 확인할 수 있습니다.")
    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="Jeonju Library Finder", page_icon="📚", layout="wide")
    ensure_session_state()
    inject_styles()
    render_auth_sidebar()
    render_admin_sidebar()

    try:
        import_status = latest_import_status()
        all_libraries = load_all_libraries()
    except requests.RequestException:
        st.error("백엔드 서버에 연결할 수 없습니다. 먼저 백엔드를 실행한 뒤 다시 접속해주세요.")
        return

    render_hero(import_status, all_libraries)
    render_admin_users_panel()

    if st.session_state.get("selected_library_id"):
        render_library_detail(all_libraries)
    else:
        selected_district = render_district_filter()
        filtered_libraries = load_libraries(selected_district)
        render_library_cards(filtered_libraries)
        render_search_section(all_libraries)


if __name__ == "__main__":
    main()





