# AI-Powered HR Hiring Assistant

A human-supervised hiring workflow that coordinates three specialized agents:

1. **Resume Scoring Agent** — evaluates resumes against an approved, job-related rubric and provides evidence-based recommendations.
2. **Candidate Screening Call Agent** — conducts consent-aware, structured candidate screening.
3. **Interview Scheduling & Invitation Agent** — coordinates interview availability and sends invitations only after explicit HR approval.

This is a decision-support and workflow-automation application. It does not make autonomous hiring or rejection decisions.

## Project status

The project is being delivered in 15 independently testable modules. See the project SRS for functional requirements, candidate lifecycle states, acceptance criteria, privacy requirements, and responsible-AI controls.

### Architecture decisions

- Frontend: React + TypeScript + Vite.
- Backend: Django; REST endpoints and API authentication are introduced in a later module.
- Workflow orchestration: LangGraph, with explicit persisted states and human approval gates.
- Initial database: SQLite for local development; PostgreSQL is the target database for the later migration.
- Initial LLM: the project's Azure-hosted GPT-4.1 mini deployment. The exact Azure deployment name is configuration, not a hard-coded model identifier.
- Candidate calling: a real voice/telephony integration is planned. The provider and destination-country coverage must be confirmed before the calling integration module.
- Email and calendar integrations must use approved credentials and must not send candidate communications without the required HR approval.

## Backend setup (Windows PowerShell)

Use Python 3.12 or another Python version supported by the pinned Django release.

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Generate a development secret key:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated value in `backend/.env` as `SECRET_KEY`. Do not commit `.env` or share its contents.

Run the backend checks and migrations:

```powershell
python manage.py check
python manage.py migrate
python manage.py runserver
```

The development settings module is selected by default. To use production settings, set `DJANGO_SETTINGS_MODULE=config.django.production` in the deployment environment and provide the required production environment variables. Never use development settings in a production deployment.

## Frontend setup

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend is currently the Vite starter application. Application screens and API integration are delivered in later modules.

## Environment configuration

See [backend/.env.example](backend/.env.example) for the complete list of configuration keys. Azure credentials are optional until the LLM integration module is implemented. Use the **exact deployment name** configured in Azure for `AZURE_OPENAI_CHAT_DEPLOYMENT`; it may differ from the underlying model name.

## Security and privacy baseline

- Secrets belong in environment variables or an approved secret manager.
- Use synthetic or consented test data during development.
- Resume files, transcripts, and candidate communications are untrusted input.
- Do not log full resumes, candidate contact details, full transcripts, or credentials.
- Human review is mandatory before screening progression and interview invitation delivery.
