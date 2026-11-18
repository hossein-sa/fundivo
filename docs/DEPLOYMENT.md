# Fundivo — Environments and Deployment

Status: **Development setup documented; production deployment not implemented.**

Fundivo currently records and manages financial activity; it does not process, hold, or transfer money. This document describes how to run the existing backend locally and lists future production requirements. It is not a production runbook.

## 1. Repository layout

- `backend/`: Django API, tests, pinned Python requirements, and example environment variables.
- `compose.yaml`: local PostgreSQL and ephemeral Redis services.
- `infra/`: reserved for future infrastructure code.
- `.github/workflows/backend-ci.yml`: automated backend checks.

The frontend may be added to this monorepo later, but is not part of the current backend MVP.

## 2. Requirements for local Windows development

- Windows with PowerShell and PyCharm
- Python 3.12
- Git
- Docker Desktop with Docker Engine and Compose

All commands below are run from the repository root, unless stated otherwise.

## 3. First-time setup

```powershell
py -3.12 -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Open `backend/.env` and replace every placeholder secret with a unique local value. For example, generate a Django secret key using:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output to `DJANGO_SECRET_KEY` **inside the ignored local `.env` file**; never paste real secrets into issues, logs or commits. Generate a different strong value for `POSTGRES_PASSWORD`. The `.env.example` file must contain placeholders only.

The current `compose.yaml` exposes PostgreSQL only at `127.0.0.1:5433` on the Windows host; within its container PostgreSQL uses port `5432`. When Django runs locally outside Docker, `POSTGRES_HOST=127.0.0.1` and `POSTGRES_PORT=5433` are appropriate.

## 4. Start the local database

```powershell
docker compose --env-file backend/.env config --quiet
docker compose --env-file backend/.env up -d db
docker compose --env-file backend/.env ps
docker compose --env-file backend/.env exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

The database uses a named Docker volume to preserve local data. **Do not run `docker compose down -v` unless you explicitly intend to erase the local database.** Changing `POSTGRES_*` environment variables does not automatically reinitialize an existing PostgreSQL volume.

## 5. Verify the backend

```powershell
python backend\manage.py check
python backend\manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('PostgreSQL connection successful'); connection.close()"
python -m ruff check backend
python -m pytest -c backend/pytest.ini backend/tests -v
python backend\manage.py spectacular --validate --fail-on-warn
```

These are the current project checks. Passing them is **not** evidence that the system is production-ready.

### Database migration safety

The Custom User Model and initial migration are implemented. After reviewing migrations, run `python backend/manage.py migrate`.

## 6. Start the development server

```powershell
python backend\manage.py runserver
```

With `API_DOCS_ENABLED=True` in the development settings, documentation is available at:

- `http://127.0.0.1:8000/api/v1/docs/`
- `http://127.0.0.1:8000/api/v1/redoc/`
- `http://127.0.0.1:8000/api/v1/schema/`

These routes are not intended for public production exposure.

## 7. Stop the local database

```powershell
docker compose --env-file backend/.env down
```

This stops and removes the containers and network but preserves the named database volume.

## 8. Continuous integration

The repository workflow uses Ubuntu, Python 3.12, a temporary PostgreSQL 17 service, and test-only environment variables. It runs Ruff, Django system checks, OpenAPI validation, a PostgreSQL connection check, and pytest. CI does not read or upload the developer's local `.env` file.

CI now checks committed migrations and applies them to its temporary PostgreSQL service.

## 9. Production deployment — not implemented

A production release must have a reviewed, repeatable deployment configuration. Before deploying:

1. Use `config.settings.production`, `DEBUG=False`, a production-only `DJANGO_SECRET_KEY`, and restricted `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`.
2. Configure a production WSGI/ASGI application server and trusted reverse proxy with HTTPS. Review proxy forwarding and HSTS settings for the actual environment.
3. Run Django deployment checks: `python backend/manage.py check --deploy --settings=config.settings.production` with production environment variables configured.
4. Isolate PostgreSQL from the public internet; provision a dedicated least-privilege database account, encrypted transport as required, backups, restore tests, and monitored storage.
5. Plan and review migrations, including zero-downtime and rollback considerations, before applying them to real data.
6. Configure static files, safe private receipt storage, monitoring, structured logs, secret rotation, and incident handling.
7. Implement and test authentication, object-level permissions, rate limiting, financial idempotency, and audit logging.
8. Review applicable privacy and legal requirements for the deployment jurisdiction.

**No production host, cloud provider, secrets manager, deployment automation, or recovery objective has been chosen yet.** Document these decisions before the first production release.

## OTP Development Service

Start both services using `docker compose --env-file backend/.env up -d db redis`.
For Django running on Windows, `REDIS_URL=redis://127.0.0.1:6379/0`.
The OTP backend stores expiring Redis challenges; Redis persistence is disabled.
The local plaintext test outbox is `backend/.otp-outbox` (ignored by Git).
It must **never** be used in production; a real SMS provider and operations
review are still required. See `docs/OTP.md`.
