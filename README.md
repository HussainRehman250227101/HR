# AI-Powered HR Hiring Assistant

A human-supervised hiring workflow with three specialized agents: resume scoring, candidate screening calls, and interview scheduling/invitations.

## Architecture and delivery

The project is developed in 15 independently tested modules. The backend is Django, the frontend React + TypeScript, orchestration LangGraph, and local development uses SQLite before the planned PostgreSQL migration. Azure GPT-5 mini is the configured LLM deployment. Pakistan (+92) is the current calling destination.

## Module 02 — Authentication & RBAC

Roles:
- **ADMIN**: HR Administrator (Django staff/superuser permissions remain separate).
- **RECRUITER**: HR Recruiter.
- **HIRING_MANAGER**: Hiring Manager.

JWT endpoints:
- `POST /api/v1/auth/token/` — obtain access and refresh tokens.
- `POST /api/v1/auth/token/refresh/` — refresh access token.
- `POST /api/v1/auth/logout/` — blacklist refresh token.
- `GET /api/v1/auth/me/` — authenticated user profile.

Role permissions are reusable classes in `accounts/permissions.py`. All API endpoints default to authenticated access. Django admin access is separately controlled by Django's staff/superuser flags.

## Backend setup (Windows PowerShell)

Use Python 3.12 and run from `backend`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a locally generated `SECRET_KEY` in `.env`. Never commit secrets.

### Module 02 first migration (SQLite only)

This module introduces `AUTH_USER_MODEL=accounts.User`. Django custom user models must be present before the initial auth migrations. If you have only the disposable Module 01 SQLite database, remove it and rebuild:

```powershell
Remove-Item .\db.sqlite3 -ErrorAction SilentlyContinue
python manage.py makemigrations accounts
python manage.py migrate
python manage.py createsuperuser
python manage.py check
python manage.py test accounts
python manage.py runserver
```

Do not delete a database containing valuable data. For a database with data, plan a dedicated user-model migration instead of resetting it.

## API usage

Login:
```http
POST /api/v1/auth/token/
Content-Type: application/json

{"username":"your_username","password":"your_password"}
```

Authenticated profile:
```http
GET /api/v1/auth/me/
Authorization: Bearer <access_token>
```

Logout:
```http
POST /api/v1/auth/logout/
Authorization: Bearer <access_token>
Content-Type: application/json

{"refresh":"<refresh_token>"}
```

Use HTTPS in production, protect refresh tokens, rotate secrets, and never store tokens in source control. The frontend token-storage strategy will be designed in its dedicated frontend/auth integration work rather than assuming localStorage is secure.
