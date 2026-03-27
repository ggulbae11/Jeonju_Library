바이브코딩으로 제작한 전주내 도서관 도서검색 시스템 입니다.

사용한 데이터파일은 아래 구글 드라이브에서 다운받아 폴더 안에 있는 두개의 파일을 따로 꺼내서 프로젝트의 data 폴더 안에 넣어서 사용하면 됩니다.
https://drive.google.com/drive/folders/1EW7djqR5e_R_D023AaUoQGSG3XnjQTfn?usp=drive_link

실행 방법은 두 개의 터미널을 열고 해당 프로젝트의 루트위치에서 (ex - C:\OSS_Library) 각각 백엔드와 프론트엔드를 실행해주면 됩니다.
백엔드 실행 : uv run --group backend uvicorn backend.main:app --reload
프론트엔드 실행 : uv run --group frontend streamlit run frontend/app.py

웹사이트에 접속 후에는 일반회원으로 회원가입하거나 이미 있는 계정으로 로그인 할 수 있습니다.

관리자 계정
 -ID: admin123
 -password: pw123
 일반회원 계정
 -ID: user1
 -password: password1

 일반 회원은 도서관/도서검색 등의 사이트 기본 기능을 사용할 수 있고, 관리자 계정은 일반회원의 기능 + 현재 가입한 사용자 목록을 볼 수 있는 기능이 있습니다.

# Jeonju Library Map

Streamlit + FastAPI + SQLite3 starter project for a public-data-powered library availability app.

## Stack

- Frontend: Streamlit
- Backend: FastAPI
- Database: SQLite3
- Required packages: pandas, requests
- Environment manager: uv

## Project Structure

```text
.
|-- backend/
|   |-- api/
|   |   `-- routes/
|   |-- core/
|   |-- schemas/
|   `-- main.py
|-- data/
|-- frontend/
|   `-- app.py
|-- .python-version
|-- pyproject.toml
`-- README.md
```

## Quick Start

### Local with uv

1. Install Python 3.12 and create the virtual environment:

   ```powershell
   uv sync --group backend --group frontend --group dev
   ```

2. Run the FastAPI server:

   ```powershell
   uv run --group backend uvicorn backend.main:app --reload
   ```

3. Run the Streamlit app:

   ```powershell
   uv run --group frontend streamlit run frontend/app.py
   ```

### Run with Docker

1. Build and start the containers:

   ```powershell
   docker compose up --build
   ```

2. Open the apps:

   - Frontend: `http://localhost:8501`
   - Backend docs: `http://localhost:8000/docs`

3. Stop the containers:

   ```powershell
   docker compose down
   ```

## Notes

- SQLite database file will be created at `data/library.db`.
- Docker persists the SQLite database through the local `data/` volume mount.
- `data/booklist.csv` is imported with `cp949` encoding.
- On first backend startup, the CSV can be imported automatically into SQLite.
- The first registered account is created with the `admin` role.
