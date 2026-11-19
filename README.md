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

## Funds API — Phase 2 (initial slice)

Authenticated users can create draft funds using `POST /api/v1/funds/`.
The creator becomes the manager in the same database transaction.
`GET /api/v1/funds/` lists only funds with an active membership.
Other routes and the current limitations are documented in [docs/FUNDS.md](docs/FUNDS.md).
Manager transfer, activation, financial settings and shares are not yet implemented.

## Invitation API (Phase 3 — initial slice)

Managers can issue mobile-bound invitation codes for draft funds. The recipient must
sign in with their verified mobile to accept or reject. Codes are returned only once,
are never stored in plaintext, and expire in 48 hours. See [Invitations](docs/INVITATIONS.md)
for the API contract and manual test procedure.

## Shares API (draft funds)

A manager can set `target_share_count` on a draft fund, allocate multiple
individual shares to active registered memberships, and safely retry allocations
using a client-generated UUID (`allocation_id`). Managers can list all shares;
ordinary members can list and read only their own shares. See [SHARES](docs/SHARES.md).
Guest membership, share transfers, money amounts and fund activation are pending.

## Guest fund memberships

Fund managers can record named guest placeholders while a fund is in draft,
without creating a login account. Guest memberships can hold draft shares but
cannot authenticate or claim ownership automatically. See
[guest membership rules](docs/GUEST_MEMBERSHIPS.md).
