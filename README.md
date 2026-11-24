# Kickoff Cinema

Coursework for the "Software Documentation and Design Patterns" course.
Variant 17: an online cinema web application with subscriptions (Free with ads / Premium without ads).

## Tech stack

- Python 3.12, FastAPI, Pydantic
- SQLAlchemy 2.0, SQLite
- HTML, CSS, JavaScript
- pytest

## How to run

1. Create and activate a virtual environment (Windows PowerShell):
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create the database with demo data:
   ```
   python seed.py
   ```
4. Prepare demo videos (requires ffmpeg):
   ```
   python prepare_media.py
   ```
5. Start the server:
   ```
   uvicorn app.main:app --reload
   ```
6. Open http://127.0.0.1:8000 (website) or http://127.0.0.1:8000/docs (API documentation).

## Run tests

```
pytest
```

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Administrator | admin@cinema.local | admin123 |
| Free user | user@cinema.local | user1234 |
| Premium user | premium@cinema.local | premium123 |

Any email starting with `declined` (for example `declined@test.com`) imitates a rejected payment.

## Project structure

- `app/` — backend: controllers, services, repositories, models, schemas, patterns
- `frontend/` — web interface
- `docs/diagrams/` — UML diagrams
- `tests/` — automated tests
- `seed.py` — demo data, `prepare_media.py` — demo videos

## Design patterns (GoF)

Builder (search), State + Flyweight (subscription), Adapter (payment), Proxy (video access),
Strategy (recommendations), Template Method (admin reports).