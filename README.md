
# Jeonju Library Map


바이브코딩으로 제작한 전주내 도서관 도서검색 시스템 입니다.

사용한 데이터파일은 아래 구글 드라이브에서 다운받아 폴더 안에 있는 두개의 파일을 따로 꺼내서 프로젝트의 data 폴더 안에 넣어서 사용하면 됩니다.
```
https://drive.google.com/drive/folders/1EW7djqR5e_R_D023AaUoQGSG3XnjQTfn?usp=drive_link
```

실행 방법은 아래의 Quick Start 부분의 Local with uv를 따라가시면 됩니다.

웹사이트에 접속 후에는 일반회원으로 회원가입하거나 이미 있는 계정으로 로그인 할 수 있습니다.

관리자 계정
```
 -ID: admin123
 -password: pw123
 ```
 
 일반회원 계정
 ```
 -ID: user1
 -password: password1
```
 일반 회원은 도서관/도서검색 등의 사이트 기본 기능을 사용할 수 있고, 관리자 계정은 일반회원의 기능 + 현재 가입한 사용자 목록을 볼 수 있는 기능이 있습니다.


 

<admin 계정으로 로그인>
```
<img width="728" height="442" alt="image" src="https://github.com/user-attachments/assets/671e2d9b-5a8a-4571-9a58-13a31d7e902a" />
<img width="392" height="310" alt="image" src="https://github.com/user-attachments/assets/765959d0-316f-41d6-b70b-72a50c7637fc" />
```
생성되어있는 관리자 계정으로 로그인하였습니다.

<사용자목록>
```
<img width="1217" height="329" alt="image" src="https://github.com/user-attachments/assets/f304b658-eb37-4039-b9c4-a80efe0b7f41" />
```
관리자 계정만 볼 수 있는 사용자 목록창입니다.

<메인화면>
```
<img width="2554" height="1265" alt="image" src="https://github.com/user-attachments/assets/48b48434-b308-4bb8-a688-31bd40f2b45d" />
```
웹사이트의 메인 화면입니다. 전주에 있는 도서관의 리스트가 있습니다.
선택하면 해당 도서관으로 이동합니다.

<전체 도서 검색>
```
<img width="1493" height="734" alt="image" src="https://github.com/user-attachments/assets/1985ac3a-4c3e-4de7-b430-83f557fb6c41" />
```
메인화면 아래에 있는 전체 도서 검색 기능입니다.
원하는 도서를 검색하면 모든 도서관에서 해당 도서를 보여줍니다.
혹은 옆의 도서관 필터로 원하는 도서관을 필터링할 수 있습니다.

<도서관 선택 후 입장>
```
<img width="1392" height="1009" alt="image" src="https://github.com/user-attachments/assets/92036e79-1cc8-45e7-8905-e1af52da58fa" />
```
원하는 도서관을 선택합니다.

<도서관 정보 및 도서 목록 / 검색창>
```
<img width="1317" height="1076" alt="image" src="https://github.com/user-attachments/assets/0aaa5c38-8ddc-4a3d-86e1-9263afee4692" />
```
도서관에 입장하면 도서관의 정보와 아래에는 보유 도서리스트가 나타납니다.
페이지를 넘겨가며 확인할 수도 있으며, 원하는 키워드로 검색할 수도 있습니다.

<같은 저자의 책>
```
<img width="588" height="262" alt="image" src="https://github.com/user-attachments/assets/12854896-ca3f-4e16-8b69-33bdb7d457f5" />
<img width="1321" height="474" alt="image" src="https://github.com/user-attachments/assets/d3ae0de4-0a05-4b61-b23f-70f4202fa336" />
```
해당 버튼을 누르면 자동으로 그 책의 저자를 검색하여 결과를 보여줍니다.




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
