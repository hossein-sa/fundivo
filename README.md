# Fundivo

Fundivo is a community fund management platform for
rotating savings and interest-free lending groups.

## Project Status

Under active development.

The backend infrastructure is being built.
Business APIs and user authentication are not implemented yet.

## Architecture

Fundivo follows a Monorepo structure with a
Modular Monolith backend.

```text
fundivo/
├── backend/       # Django REST API
├── infra/         # Infrastructure files
├── compose.yaml   # Local PostgreSQL
└── README.md
```

## Tech Stack

- Python 3.12
- Django 5.2 LTS
- Django REST Framework
- PostgreSQL 17
- Docker Compose
- pytest / pytest-django
- Ruff
- drf-spectacular

## Local Development

### Prerequisites

- Python 3.12
- Docker Desktop
- Git

### 1. Clone the repository

```powershell
git clone https://github.com/hossein-sa/fundivo.git
cd fundivo
```

### 2. Create a virtual environment

```powershell
py -3.12 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r backend\requirements.txt
```

### 4. Configure environment variables

```powershell
Copy-Item backend\.env.example backend\.env
```

Edit `backend/.env` and replace the placeholder
Django secret key and PostgreSQL password with
secure, randomly generated values.

Never commit `.env`.

### 5. Start PostgreSQL

```powershell
docker compose --env-file backend/.env up -d db
```

### 6. Verify Django

```powershell
python backend\manage.py check
```

Run database migrations: `python backend\manage.py migrate`.

### 7. Run the development server

```powershell
python backend\manage.py runserver
```

## API Documentation

Available in the development environment:

- Swagger UI: http://127.0.0.1:8000/api/v1/docs/
- ReDoc: http://127.0.0.1:8000/api/v1/redoc/
- OpenAPI: http://127.0.0.1:8000/api/v1/schema/

## Tests

```powershell
python -m pytest -c backend/pytest.ini backend/tests -v
```

## Code Quality

```powershell
python -m ruff check backend
```

## License

Not specified yet.

## OTP Local Verification

Start PostgreSQL and Redis: `docker compose --env-file backend/.env up -d db redis`.
Use `POST /api/v1/auth/otp/request/` and `POST /api/v1/auth/otp/verify/`.
In local development the code is written to **ignored** `backend/.otp-outbox`.
Never upload that file; remove it when finished. OTP verification returns a
short-lived login ticket; JWT issuance is implemented; see docs/JWT.md. See `docs/OTP.md`.

## JWT authentication (Phase 1)

After OTP verification, exchange the one-time `login_ticket` at
`POST /api/v1/auth/token/exchange/` for a JWT `access` and `refresh` pair.
Use `Authorization: Bearer <access>` for protected APIs including `GET /api/v1/auth/me/`.
Rotate refresh tokens at `POST /api/v1/auth/token/refresh/` and revoke a refresh token
at `POST /api/v1/auth/logout/` (requires an access token).

Install dependencies with `python -m pip install -r backend/requirements.txt`.
Add a strong, independent `JWT_SIGNING_KEY` to your **untracked** `backend/.env`.
Apply Simple JWT blacklist migrations: `python backend/manage.py migrate`.
See `docs/JWT.md` for examples and security limitations.
