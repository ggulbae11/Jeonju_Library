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
