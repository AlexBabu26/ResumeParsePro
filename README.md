# Parse Pro AI - Resume Parsing Application

AI-powered resume parsing application for recruiters built with Django and OpenRouter LLM.

## Features

- **Resume Upload**: Upload PDF and DOCX resume files
- **AI Extraction**: Uses OpenRouter LLM to extract structured data from resumes
- **AI Classification**: Automatically classifies candidates into roles and seniority levels
- **AI Summary**: Generates recruiter-friendly summaries and highlights
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
- OpenRouter API key ([Get one here](https://openrouter.ai/))

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
   
   # Optional: Classification and Summary models (defaults to EXTRACT_MODEL if not set)
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

- `POST /api/v1/resumes/upload/` - Upload a resume (multipart/form-data)
  - Requires: `file` (PDF or DOCX)
  - Returns: `resume_document_id`, `parse_run_id`, `status`, `candidate_id`

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
- `anthropic/claude-3-haiku`
- `google/gemini-pro`
- `meta-llama/llama-3-8b-instruct`

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

The application follows a 3-stage pipeline:

1. **Input & Extraction**: Upload → Text extraction → Cleaning
2. **Core Parsing**: LLM extraction → Validation → Normalization
3. **Output & Analysis**: Database persistence → Search/Filter → Detail views

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

