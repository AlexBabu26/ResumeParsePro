# Parse Pro AI - Resume Parsing Application

AI-powered resume parsing application for recruiters built with Django and OpenRouter LLM.

## Features

- **Resume Upload**: Upload PDF and DOCX resume files (Single & Bulk support)
- **AI Extraction**: Uses OpenRouter LLM with automated fallback to **Groq API**
- **Requirement Filtering**: Automatically accept or reject candidates based on job-specific criteria (skills, experience, education, etc.)
- **AI Classification**: Automatically classifies candidates into roles and seniority levels
- **AI Summary**: Generates recruiter-friendly summaries and highlights
- **Asynchronous Processing**: Scalable background processing with Celery and Redis
- **Anti-Hallucination**: Regex verification of contact information (email, phone, links)
- **Normalized Storage**: Stores candidate data in normalized relational database
- **Search & Filter**: Search candidates by name, skills, role, confidence, etc.
- **JWT Authentication**: Secure API access with JWT tokens

## Project Structure

```
parsepro/
├── config/              # Django project settings
├── accounts/            # Authentication app (JWT)
├── resumes/             # Resume upload and parsing
├── candidates/          # Candidate search and management
├── manage.py
└── pyproject.toml
```

## Prerequisites

- Python 3.10+
- Redis Server (for background tasks)
- OpenRouter API key ([Get one here](https://openrouter.ai/))
- Groq API key (Optional fallback, [Get one here](https://console.groq.com/))

## Installation

1. **Clone the repository** (if applicable) or navigate to the project directory

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```
   Or if using uv:
   ```bash
   uv pip install -e .
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```bash
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   OPENROUTER_API_KEY=your-openrouter-api-key-here
   OPENROUTER_EXTRACT_MODEL=openai/gpt-4o-mini
   OPENROUTER_TEMPERATURE=0.1
   
   # Groq Fallback (Optional but Recommended)
   GROQ_API_KEY=your-groq-api-key-here
   
   # Celery & Redis
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   RESUME_PARSE_ASYNC=True
   
   # Optional: Classification and Summary models
   OPENROUTER_CLASSIFY_MODEL=openai/gpt-4o-mini
   OPENROUTER_SUMMARY_MODEL=openai/gpt-4o-mini
   OPENROUTER_CLASSIFY_TEMPERATURE=0.1
   OPENROUTER_SUMMARY_TEMPERATURE=0.2
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser** (for Django admin):
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to create an admin user.

6. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

7. **Start the Celery worker** (in a separate terminal):
   ```bash
   # Windows (using eventlet)
   celery -A config worker -P eventlet -l info
   
   # Linux/Mac
   celery -A config worker -l info
   ```

The API will be available at `http://localhost:8000/api/v1/`

## API Endpoints

### Authentication

- `POST /api/v1/auth/register/` - Register a new user
  ```json
  {
    "username": "recruiter1",
    "email": "recruiter@example.com",
    "password": "securepassword",
    "password2": "securepassword"
  }
  ```

- `POST /api/v1/auth/token/` - Get JWT access token
  ```json
  {
    "username": "recruiter1",
    "password": "securepassword"
  }
  ```

- `POST /api/v1/auth/token/refresh/` - Refresh access token

### Resumes

- `POST /api/v1/resumes/upload/` - Upload a resume
  - Multipart parameters:
    - `file`: Resume file (PDF/DOCX)
    - `requirements`: (Optional) JSON string of filtering criteria
  - Returns: `resume_document_id`, `parse_run_id`, `status`

- `POST /api/v1/resumes/bulk-upload/` - Upload multiple resumes
  - Multipart parameters:
    - `files`: List of resume files
    - `requirements`: (Optional) JSON string of filtering criteria
  - Returns: Summary of all uploads (Accepted/Rejected counts)

#### Requirement Filtering JSON format:
```json
{
  "required_skills": ["Python", "Django"],
  "min_years_experience": 3,
  "required_education_degree": ["Bachelor", "Master"],
  "required_primary_role": ["Software Engineer"],
  "use_llm_validation": true
}
```

- `GET /api/v1/resume-documents/` - List uploaded resume documents
- `GET /api/v1/parse-runs/{id}/` - Get parse run status and details
- `POST /api/v1/parse-runs/{id}/retry/` - Retry parsing a failed resume

### Candidates

- `GET /api/v1/candidates/` - List candidates with filters
  - Query parameters:
    - `q` - Search query (name, headline, location, role, company, title)
    - `skill` - Filter by skill name (exact match, case-insensitive)
    - `role` - Filter by primary role
    - `min_conf` - Minimum confidence score (0.0-1.0)
    - `page` - Page number (default: 1)
    - `page_size` - Results per page (default: 20)
  
  Example: `/api/v1/candidates/?skill=Python&min_conf=0.7&q=developer`

- `GET /api/v1/candidates/{id}/` - Get candidate details (includes skills, education, experience)

- `PATCH /api/v1/candidates/{id}/` - Update candidate (human-in-the-loop editing)

## Usage Example

1. **Register and get token**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register/ \
     -H "Content-Type: application/json" \
     -d '{"username":"recruiter1","email":"recruiter@example.com","password":"password123","password2":"password123"}'
   
   curl -X POST http://localhost:8000/api/v1/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"recruiter1","password":"password123"}'
   ```

2. **Upload a resume**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/resumes/upload/ \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -F "file=@resume.pdf"
   ```

3. **Search candidates**:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/candidates/?skill=Python&min_conf=0.7" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

## Data Model

### ResumeDocument
- Stores uploaded file and extracted raw text
- Tracks extraction method (pdfminer, python-docx)

### ParseRun
- Tracks each parsing attempt
- Stores raw LLM JSON, normalized JSON, warnings, errors
- Status: queued, processing, success, partial, failed

### Candidate
- Normalized candidate profile
- Links to ResumeDocument and ParseRun
- Stores contact info, role, seniority, confidence

### Skill, EducationEntry, ExperienceEntry
- Related tables for searchable candidate data
- Each entry includes confidence score and evidence

## Configuration

### OpenRouter Models

Default model is `openai/gpt-4o-mini`. You can configure separate models for extraction, classification, and summary:

**Extraction** (required):
```
OPENROUTER_EXTRACT_MODEL=openai/gpt-4o-mini
OPENROUTER_TEMPERATURE=0.1
```

**Classification** (optional, defaults to EXTRACT_MODEL):
```
OPENROUTER_CLASSIFY_MODEL=openai/gpt-4o-mini
OPENROUTER_CLASSIFY_TEMPERATURE=0.1
```

**Summary** (optional, defaults to EXTRACT_MODEL):
```
OPENROUTER_SUMMARY_MODEL=openai/gpt-4o-mini
OPENROUTER_SUMMARY_TEMPERATURE=0.2
```

Other compatible models:
- `meta-llama/llama-3-8b-instruct`

### Groq Configuration

Groq is used as a high-speed fallback when OpenRouter hit rate limits.

**API Key**:
```
GROQ_API_KEY=your-groq-api-key-here
```

**Fallback Model**:
The system is hardcoded to use **`llama-3.3-70b-versatile`** for Groq fallbacks to ensure high-quality extraction and JSON mode support.

### Temperature

Lower temperature (0.0-0.2) for more deterministic extraction. Summary can use slightly higher temperature (0.2) for more natural language.

## Development

### Running Tests

```bash
python manage.py test
```

### Creating Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Django Admin

Access admin panel at `http://localhost:8000/admin/` after creating a superuser.

## Architecture

The application follows a resilient 3-stage pipeline:

1. **Input & Extraction**: Upload → Text extraction → Cleaning → PII extraction (regex)
2. **Core Parsing**: 
   - Primary: OpenRouter LLM
   - Fallback: **Groq API** (triggered automatically on 429 rate limits)
   - Validation & Normalization
3. **Analysis & Filtering**: 
   - Enrichment (Classification/Summary)
   - Requirement Validation (LLM-based or string-based)
   - Database persistence

### Resilience & Fallbacks

- **Provider Fallback**: If OpenRouter returns a 429, the system immediately switches to Groq to ensure service continuity.
- **Model Fallback**: Within OpenRouter, multiple models are tried in sequence if the primary is unavailable.
- **Rate Limit Handling**: The Groq client respects `Retry-After` headers and tracks quota usage via `x-ratelimit` headers.

### Anti-Hallucination Strategy

1. Regex extraction of emails/phones/links from raw text
2. Pass verified PII to LLM as "known facts"
3. Post-validation: drop any LLM-provided contact info not found in regex results

### Validation Pipeline

- JSON schema validation
- Email/phone/link verification
- Date normalization (Present → null, is_current=True)
- Skill deduplication
- Evidence substring verification
- Confidence scoring

## Troubleshooting

### "OPENROUTER_API_KEY is not configured"
- Ensure `.env` file exists with `OPENROUTER_API_KEY` set

### "Text extraction failed"
- Check that uploaded file is valid PDF or DOCX
- Ensure `pdfminer.six` and `python-docx` are installed

### "LLM_INVALID_JSON" error
- LLM returned invalid JSON - try retry endpoint or check model compatibility

### Database errors
- Run `python manage.py migrate` to apply migrations
- Check SQLite file permissions

## License

This project is for academic/educational purposes.

## Support

For issues or questions, please check the codebase documentation or create an issue in the repository.

