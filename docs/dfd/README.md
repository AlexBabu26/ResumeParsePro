# Data Flow Diagrams - Resume Parse Pro AI

This folder contains the Data Flow Diagrams (DFDs) for the Resume Parse Pro AI system at various decomposition levels.

---

## Windows 11 Installation Guide

Complete installation instructions for running Resume Parse Pro AI on a Windows 11 machine with Python, uv, Redis, and Celery.

### Prerequisites Overview

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.10+ | Runtime |
| uv | Latest | Package manager |
| Redis (or Memurai) | 7.x compatible | Celery broker & result backend |
| Celery | 5.3+ | Async task queue (installed via uv) |

### Step 1: Install Python 3.10+

1. Download Python from python.org/downloads
2. Run the installer and enable **"Add Python to PATH"**
3. Verify: `python --version` (should show 3.10.x or higher)

### Step 2: Install uv

In PowerShell:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or with WinGet: `winget install --id=astral-sh.uv -e`

Add uv to PATH if needed (typically `%USERPROFILE%\.local\bin`). Restart PowerShell, then verify: `uv --version`

### Step 3: Install Redis (or Memurai)

Redis does not officially support Windows. Choose one option:

**Option A: Memurai Developer (recommended for Windows)**

- Download from memurai.com/get-memurai
- Run the MSI installer, use default port 6379
- Memurai is Redis-compatible; no code changes needed

**Option B: WSL2 + Redis**

- Enable WSL2: `wsl --install`
- In Ubuntu (WSL): `sudo apt update && sudo apt install redis-server && sudo service redis-server start`

**Option C: Docker**

- Install Docker Desktop for Windows
- Run: `docker run -d -p 6379:6379 --name redis redis:7-alpine`

Verify: `memurai-cli ping` (or `wsl redis-cli ping`) — expected response: PONG

### Step 4: Clone and Set Up the Project

1. Clone or copy the project to your machine
2. Create virtual environment and install dependencies:

   ```
   uv venv
   .\.venv\Scripts\Activate.ps1
   uv sync
   ```

   If you get an execution policy error: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

3. Verify: `python -c "import django; print(django.VERSION)"`

### Step 5: Environment Variables

Create a `.env` file in the project root. **All sensitive keys (including OPENROUTER_API_KEY) must be stored only in `.env` — never hardcode them in source code.**

Required variables:

- `SECRET_KEY` — Django secret (change in production)
- `DEBUG` — True for development
- `ALLOWED_HOSTS` — localhost,127.0.0.1
- `OPENROUTER_API_KEY` — Get from openrouter.ai (required for AI parsing)
- `OPENROUTER_EXTRACT_MODEL` — e.g. nvidia/nemotron-3-nano-30b-a3b:free
- `OPENROUTER_TEMPERATURE` — 0.1 recommended
- `CELERY_BROKER_URL` — redis://localhost:6379/0 (default)
- `CELERY_RESULT_BACKEND` — redis://localhost:6379/0 (default)
- `RESUME_PARSE_ASYNC` — 1 to use Celery

### Step 6: Database Migrations

```
python manage.py migrate
python manage.py createsuperuser
```

### Step 7: Run the Application

Three processes must run:

1. **Terminal 1 — Django:** `python manage.py runserver`
2. **Terminal 2 — Celery worker:** `celery -A config worker -l info -P solo` (use `-P solo` on Windows)
3. **Redis/Memurai** — Ensure the service is running on port 6379

### Verification

- Django: http://localhost:8000
- API docs: http://localhost:8000/api/schema/swagger-ui/
- Admin: http://localhost:8000/admin/

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `celery: command not found` | Activate venv: `.\.venv\Scripts\Activate.ps1` |
| Connection refused to Redis | Ensure Redis/Memurai is running on port 6379 |
| `fork()` error with Celery | Use `-P solo` when starting the worker |
| OPENROUTER_API_KEY not configured | Add key to `.env` file (never in source code) |
| Execution policy error | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |

### Security Note

**OPENROUTER_API_KEY and other secrets must only be stored in the `.env` file.** The `.env` file is listed in `.gitignore` and must never be committed to version control. The application reads these values at runtime via `os.getenv()` — no API keys or credentials should appear in source code.

---

## Diagram Index

### Context Level (Level 0)
| File | Description |
|------|-------------|
| `dfd_level_0.svg` | Context diagram showing the system boundary with USER and ADMIN entities |

### Level 1 - Main Modules
| File | Description |
|------|-------------|
| `dfd_level_1_admin.svg` | Admin module overview - User Management, Resume Management, Candidate Management |
| `dfd_level_1_user.svg` | User module overview - All user functionalities including resume upload, search, and editing |
| `dfd_level_1_authentication.svg` | Authentication module - Registration, Login, Token Management |

### Level 1.1 - Admin Sub-modules
| File | Description |
|------|-------------|
| `dfd_level_1_1_admin_user_management.svg` | Admin User Management - View users, Activate/Deactivate, View activity |
| `dfd_level_1_2_admin_resume_monitoring.svg` | Admin Resume Monitoring - View documents, Monitor parse status, Retry failed parses |

### Level 1.1-1.3 - User Sub-modules
| File | Description |
|------|-------------|
| `dfd_level_1_1_user_resume_management.svg` | User Resume Management - Upload, Extract, Parse, View status, Retry |
| `dfd_level_1_2_user_candidate_management.svg` | User Candidate Management - Search, Filter, View details, Edit candidates |
| `dfd_level_1_3_ai_processing_pipeline.svg` | AI Processing Pipeline - Text extraction, LLM processing, Validation, Storage |

## DFD Notation Guide

### Symbols Used

| Symbol | Meaning |
|--------|---------|
| Rectangle | External Entity (USER, ADMIN) |
| Circle/Ellipse | Process |
| Open-ended Rectangle (right side open) | Data Store |
| Arrow | Data Flow |

### Data Stores

| Data Store | Description |
|------------|-------------|
| `users` | User account information |
| `admins` | Administrator accounts |
| `resume_documents` | Uploaded resume files and extracted text |
| `parse_runs` | Parsing attempt records with status and results |
| `parse_run_status_logs` | Detailed status change logs for parse runs |
| `candidates` | Normalized candidate profiles |
| `skills` | Candidate skills with confidence scores |
| `education_entries` | Education history for candidates |
| `experience_entries` | Work experience for candidates |
| `candidate_edit_logs` | Audit logs for candidate edits |
| `jwt_tokens` | JWT access tokens |
| `refresh_tokens` | JWT refresh tokens |

## System Overview

The Resume Parse Pro AI system provides:

1. **Authentication** - JWT-based secure API access
2. **Resume Upload & Parsing** - PDF/DOCX upload with AI-powered extraction
3. **AI Pipeline** - LLM extraction, validation, classification, and summarization
4. **Candidate Management** - Search, filter, view, and edit candidate profiles
5. **Admin Functions** - User management and system monitoring

## External Systems

- **OpenRouter LLM API** - External AI service for resume data extraction, classification, and summary generation
