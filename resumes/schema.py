"""
JSON Schema for resume extraction output.

This schema defines the expected structure of LLM-extracted resume data.
It includes validation for:
- Candidate contact information
- Skills with evidence
- Education history
- Work experience
- Projects and certifications
- AI-generated classification and summary
- Quality metrics
"""

# Email format pattern (simplified for regex compatibility)
EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# URL format pattern
URL_PATTERN = r"^https?://.*$"

# Date format pattern (YYYY-MM-DD, YYYY-MM, or YYYY)
DATE_PATTERN = r"^\d{4}(-\d{2})?(-\d{2})?$"


RESUME_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "candidate", "skills", "education", "experience", "quality"],
    "additionalProperties": True,  # Allow additional fields for flexibility
    "properties": {
        "schema_version": {
            "type": "string",
            "description": "Schema version identifier",
            "pattern": r"^\d+\.\d+$",
        },
        "candidate": {
            "type": "object",
            "description": "Core candidate information",
            "required": ["full_name", "emails", "phones", "links"],
            "additionalProperties": False,
            "properties": {
                "full_name": {
                    "type": ["string", "null"],
                    "minLength": 1,
                    "maxLength": 255,
                    "description": "Candidate's full name",
                },
                "headline": {
                    "type": ["string", "null"],
                    "maxLength": 255,
                    "description": "Professional headline or tagline",
                },
                "location": {
                    "type": ["string", "null"],
                    "maxLength": 255,
                    "description": "Current location (city, state, country)",
                },
                "emails": {
                    "type": "array",
                    "items": {"type": "string", "format": "email"},
                    "description": "Email addresses",
                },
                "phones": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Phone numbers",
                },
                "links": {
                    "type": "object",
                    "description": "Professional links",
                    "required": ["linkedin", "github", "portfolio", "other"],
                    "additionalProperties": False,
                    "properties": {
                        "linkedin": {
                            "type": ["string", "null"],
                            "format": "uri",
                            "description": "LinkedIn profile URL",
                        },
                        "github": {
                            "type": ["string", "null"],
                            "format": "uri",
                            "description": "GitHub profile URL",
                        },
                        "portfolio": {
                            "type": ["string", "null"],
                            "format": "uri",
                            "description": "Portfolio/personal website URL",
                        },
                        "other": {
                            "type": "array",
                            "items": {"type": "string", "format": "uri"},
                            "description": "Other relevant URLs",
                        },
                    },
                },
            },
        },
        "skills": {
            "type": "array",
            "description": "Technical and professional skills",
            "items": {
                "type": "object",
                "required": ["name", "confidence", "evidence"],
                "additionalProperties": False,
                "properties": {
                    "name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 100,
                        "description": "Skill name",
                    },
                    "category": {
                        "type": ["string", "null"],
                        "maxLength": 100,
                        "description": "Skill category (e.g., Programming, Framework, Tool)",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence score for this extraction (0-1)",
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Text snippets from resume supporting this skill",
                    },
                },
            },
        },
        "education": {
            "type": "array",
            "description": "Educational background",
            "items": {
                "type": "object",
                "required": ["institution", "degree", "start_date", "end_date", "confidence", "evidence"],
                "additionalProperties": False,
                "properties": {
                    "institution": {
                        "type": ["string", "null"],
                        "maxLength": 255,
                        "description": "Name of school/university",
                    },
                    "degree": {
                        "type": ["string", "null"],
                        "maxLength": 255,
                        "description": "Degree type (e.g., BS, MS, PhD, MBA)",
                    },
                    "field_of_study": {
                        "type": ["string", "null"],
                        "maxLength": 255,
                        "description": "Major or field of study",
                    },
                    "start_date": {
                        "type": ["string", "null"],
                        "description": "Start date (YYYY-MM-DD, YYYY-MM, or YYYY)",
                    },
                    "end_date": {
                        "type": ["string", "null"],
                        "description": "End date (null if current)",
                    },
                    "grade": {
                        "type": ["string", "null"],
                        "maxLength": 50,
                        "description": "GPA or grade achieved",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "experience": {
            "type": "array",
            "description": "Work experience history",
            "items": {
                "type": "object",
                "required": ["company", "title", "start_date", "end_date", "is_current", "bullets", "technologies", "confidence", "evidence"],
                "additionalProperties": False,
                "properties": {
                    "company": {
                        "type": ["string", "null"],
                        "maxLength": 255,
                        "description": "Company or organization name",
                    },
                    "title": {
                        "type": ["string", "null"],
                        "maxLength": 255,
                        "description": "Job title",
                    },
                    "employment_type": {
                        "type": ["string", "null"],
                        "enum": [None, "full-time", "part-time", "contract", "freelance", "internship"],
                        "description": "Type of employment",
                    },
                    "start_date": {
                        "type": ["string", "null"],
                        "description": "Start date",
                    },
                    "end_date": {
                        "type": ["string", "null"],
                        "description": "End date (null if current)",
                    },
                    "is_current": {
                        "type": "boolean",
                        "description": "Whether this is the current position",
                    },
                    "location": {
                        "type": ["string", "null"],
                        "maxLength": 255,
                        "description": "Job location",
                    },
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Responsibility/achievement bullet points",
                    },
                    "technologies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Technologies used in this role",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "projects": {
            "type": "array",
            "description": "Personal or professional projects",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "name": {
                        "type": ["string", "null"],
                        "maxLength": 255,
                        "description": "Project name",
                    },
                    "description": {
                        "type": ["string", "null"],
                        "description": "Project description",
                    },
                    "url": {
                        "type": ["string", "null"],
                        "format": "uri",
                        "description": "Project URL (GitHub, demo, etc.)",
                    },
                    "technologies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Technologies used",
                    },
                    "start_date": {"type": ["string", "null"]},
                    "end_date": {"type": ["string", "null"]},
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "certifications": {
            "type": "array",
            "description": "Professional certifications",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "name": {
                        "type": ["string", "null"],
                        "maxLength": 255,
                        "description": "Certification name",
                    },
                    "issuer": {
                        "type": ["string", "null"],
                        "maxLength": 255,
                        "description": "Issuing organization",
                    },
                    "date_issued": {
                        "type": ["string", "null"],
                        "description": "Date issued",
                    },
                    "date_expires": {
                        "type": ["string", "null"],
                        "description": "Expiration date (if applicable)",
                    },
                    "credential_id": {
                        "type": ["string", "null"],
                        "description": "Credential/certificate ID",
                    },
                    "url": {
                        "type": ["string", "null"],
                        "format": "uri",
                        "description": "Verification URL",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "classification": {
            "type": ["object", "null"],
            "description": "AI-generated role and seniority classification",
            "additionalProperties": True,
            "properties": {
                "primary_role": {
                    "type": ["string", "null"],
                    "maxLength": 100,
                    "description": "Primary job role classification",
                },
                "secondary_roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3,
                    "description": "Alternative role classifications",
                },
                "seniority": {
                    "type": ["string", "null"],
                    "enum": [None, "Intern", "Junior", "Mid", "Senior", "Staff", "Principal", "Lead/Manager"],
                    "description": "Seniority level",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Classification confidence",
                },
                "rationale": {
                    "type": ["string", "null"],
                    "description": "Explanation for the classification",
                },
            },
        },
        "summary": {
            "type": ["object", "null"],
            "description": "AI-generated recruiter summary",
            "additionalProperties": True,
            "properties": {
                "one_liner": {
                    "type": ["string", "null"],
                    "maxLength": 200,
                    "description": "Single sentence summary of the candidate",
                },
                "highlights": {
                    "type": "array",
                    "items": {"type": "string", "maxLength": 150},
                    "maxItems": 5,
                    "description": "Key highlights/strengths",
                },
            },
        },
        "quality": {
            "type": "object",
            "description": "Extraction quality metrics",
            "required": ["warnings", "missing_critical_fields", "overall_confidence"],
            "additionalProperties": True,
            "properties": {
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Extraction warnings and notes",
                },
                "missing_critical_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Critical fields that could not be extracted",
                },
                "overall_confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Overall extraction confidence score",
                },
                "enrichment_cost_usd": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Cost of AI enrichment in USD",
                },
            },
        },
    },
}

