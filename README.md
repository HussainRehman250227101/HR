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


## Module 03 — Requisition Management

The requisitions API manages job requests before candidate intake. It includes a UUID reference, role title, department, location, employment type, work mode, job description, responsibilities, required skills, minimum experience, education requirements, optional salary range/currency, headcount, hiring manager, target close date, status, and system timestamps.

Lifecycle statuses are **DRAFT**, **OPEN**, **ON_HOLD**, and **CLOSED**. A closed requisition cannot be reopened. Only draft requisitions can be deleted; active roles should be closed rather than deleted. The API records the opening/closing timestamp when the status changes.

Access:
- **HR Administrator / superuser:** read and manage all requisitions.
- **HR Recruiter:** read and manage all requisitions.
- **Hiring Manager:** read only requisitions assigned to that manager.
- Anonymous users: no access.

Endpoints under `/api/v1/requisitions/`:
- `GET /` — paginated list; optional `status`, `department`, and `search` filters.
- `POST /` — create a draft requisition (or explicitly create with another allowed status).
- `GET /<reference_code>/` — retrieve.
- `PUT/PATCH /<reference_code>/` — update, subject to role and lifecycle rules.
- `DELETE /<reference_code>/` — delete draft requisitions only.

### Module 03 database migration

The Module 02 `accounts/0001_initial.py` migration is included in the latest base commit. Generate and commit the requisitions migration on this feature branch:

```powershell
python manage.py makemigrations requisitions
python manage.py migrate --fake-initial
python manage.py makemigrations --check --dry-run
```

`--fake-initial` also supports a local Module 02 SQLite database whose accounts table was created before its initial migration was committed. Back up any important database before running migrations.

Run tests with:

```powershell
python manage.py check
python manage.py test accounts requisitions
```


## Modules 04–06 — Candidate Intake, Resume Processing and LLM Infrastructure

### Module 04 — Candidate & Resume Intake

Candidate records are linked to an **OPEN** requisition. Candidate identity/contact fields include full name, email, phone, location and LinkedIn URL. Contact and recording consent both start as **PENDING**; creating a record never assumes consent. Candidate status uses the lifecycle names in the project brief and is read-only through the intake API. Later workflow modules own human-approved progression.

Batch resume intake creates placeholder candidates with `identity_review_required=true`; it never fabricates names or email addresses from filenames.

Access:
- HR Administrator and Recruiter: create, update and view candidate records.
- Hiring Manager: read only candidates linked to requisitions assigned to that manager.
- Resume file download: HR Administrator and Recruiter only.

### Module 05 — Resume Processing Pipeline

PDF and DOCX uploads are checked for file suffix, signature/container, non-zero size, DOCX archive integrity and decompression limits. Default limits are 10 MB per file, 20 files per batch and 50 MB aggregate per batch; settings are configurable in `.env`.

Uploaded files are stored privately under `MEDIA_ROOT/resumes/` using opaque server-generated paths. The API does not expose file paths or extracted resume text. Downloads use an authenticated endpoint with private/no-store response headers.

Text extraction is local using `pypdf` and `python-docx`; resume contents are not sent to Azure during intake or extraction. Password-protected, corrupted, scanned PDFs without selectable text and unreadable documents are flagged for **Needs Manual Review**. OCR is not included in this module.

Resume uploads are persisted as **PENDING** jobs. Process them in a separate worker process:

```powershell
python manage.py process_pending_resumes --limit 20
```

An authorized recruiter can also process one pending document with `POST /api/v1/candidates/resume-documents/<resume_uuid>/process/`. An unexpected processing failure can be retried using `POST /api/v1/candidates/resume-documents/<resume_uuid>/retry/`. Content-related errors such as scanned/password-protected documents need manual intervention or a new copy. The management command provides a database-backed worker loop for the prototype; a production deployment should run it under a process supervisor or move the queue to a managed job system and add malware scanning before accepting real applicant files.

### Candidate API

Base URL: `/api/v1/candidates/`

- `GET /` — paginated candidate list; optional `status`, `requisition` (requisition UUID) and `search`.
- `POST /` — create candidate against an open requisition.
- `GET /<candidate_uuid>/` — candidate profile and resume metadata.
- `PATCH /<candidate_uuid>/` — update candidate profile; lifecycle status is read-only.
- `POST /<candidate_uuid>/resumes/` — upload a PDF/DOCX (multipart field `file`).
- `POST /requisition/<requisition_uuid>/resume-batches/` — batch upload (multipart field `files`, repeat for each resume).
- `GET /<candidate_uuid>/events/` — event history.
- `GET /resume-documents/<resume_uuid>/` — processing state and sanitized extraction metadata.
- `GET /resume-documents/<resume_uuid>/download/` — HR-only private file download.
- `POST /resume-documents/<resume_uuid>/process/` — process one pending document.
- `POST /resume-documents/<resume_uuid>/retry/` — retry an unexpected processing failure.

### Module 06 — LLM Infrastructure

The reusable client uses the OpenAI Python SDK with the Azure OpenAI v1 API endpoint `https://<resource>.openai.azure.com/openai/v1/`. Its `model` parameter is the exact Azure deployment name supplied in `AZURE_OPENAI_CHAT_DEPLOYMENT`; it is not hard-coded to a model identifier.

The shared service provides:
- Plain-text chat generation.
- Pydantic-validated structured output.
- Configurable timeout, retries, reasoning effort and completion-token budget.
- Logging of provider/deployment and exception type only; no prompts, resume content, contact information or API keys.
- A reusable guardrail treating uploaded candidate documents as untrusted data.
- Admin-only configuration status and optional connectivity-check endpoints.

`GET /api/v1/ai/status/` reports deployment configuration without exposing secrets. `POST /api/v1/ai/test/` sends one small structured-output request and consumes model quota. Automated unit tests mock the SDK and do not call Azure.

This module creates shared LLM infrastructure only. Resume scoring remains Module 07 and must be explainable, evidence-based and a prioritization aid—not an autonomous hiring decision.

### Added environment variables

```dotenv
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE-NAME.openai.azure.com
AZURE_OPENAI_API_KEY=your-key-in-local-env-only
AZURE_OPENAI_CHAT_DEPLOYMENT=YOUR-GPT-5-MINI-DEPLOYMENT-NAME
AZURE_OPENAI_TIMEOUT_SECONDS=30
AZURE_OPENAI_MAX_RETRIES=2
AZURE_OPENAI_REASONING_EFFORT=low
AZURE_OPENAI_MAX_COMPLETION_TOKENS=2000
RESUME_MAX_FILE_SIZE_MB=10
RESUME_MAX_BATCH_FILES=20
RESUME_MAX_BATCH_TOTAL_MB=50
```

Never commit `.env` or real candidate resumes. Use synthetic or consented test data. Set an approved retention/deletion policy, HTTPS, encrypted storage and malware scanning before production use.


### Verifying Modules 04–06 locally

From `backend`, after installing `requirements.txt`, generate the candidate schema migration and apply it:

```powershell
python manage.py makemigrations candidates
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test accounts requisitions candidates llm
```

The Azure connectivity test is an explicit live request and is not called during automated tests. Use `GET /api/v1/ai/status/` to check configuration first, then `POST /api/v1/ai/test/` only when you intend to consume model quota.
