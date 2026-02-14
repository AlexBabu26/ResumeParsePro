#!/usr/bin/env python3
"""Generate PDF documentation of the database schema for Resume Parse Pro AI."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

# Table data: (table_name, [(column, description, constraints, pk_fk), ...])
TABLES = [
    (
        "auth_user",
        "Django built-in; referenced by uploaded_by, edited_by",
        [
            ("id", "User ID", "NOT NULL", "PK"),
            ("username", "Username", "NOT NULL, UNIQUE", ""),
            ("password", "Hashed password", "NOT NULL", ""),
            ("email", "Email address", "", ""),
            ("first_name", "First name", "", ""),
            ("last_name", "Last name", "", ""),
            ("is_staff", "Staff status", "NOT NULL", ""),
            ("is_active", "Active status", "NOT NULL", ""),
            ("is_superuser", "Superuser status", "NOT NULL", ""),
            ("date_joined", "Join timestamp", "NOT NULL", ""),
            ("last_login", "Last login timestamp", "", ""),
        ],
    ),
    (
        "resumes_resumedocument",
        "",
        [
            ("id", "Document ID", "NOT NULL", "PK"),
            ("original_filename", "Original file name", "NOT NULL, max 255", ""),
            ("file", "File path", "NOT NULL", ""),
            ("mime_type", "MIME type", "NOT NULL, max 100", ""),
            ("file_hash", "SHA256 hash", "max 64, indexed", ""),
            ("file_size", "File size in bytes", "default 0", ""),
            ("raw_text", "Extracted text", "", ""),
            ("extraction_method", "Method used for extraction", "max 50", ""),
            ("uploaded_by_id", "Uploader user ID", "", "FK → auth_user"),
            ("created_at", "Creation timestamp", "default now", ""),
            ("updated_at", "Last update timestamp", "auto", ""),
        ],
    ),
    (
        "resumes_parserun",
        "",
        [
            ("id", "Parse run ID", "NOT NULL", "PK"),
            ("resume_document_id", "Resume document ID", "NOT NULL", "FK → resumes_resumedocument"),
            ("status", "Parse status", "queued/processing/success/partial/failed", ""),
            ("progress_stage", "Processing stage", "queued/extracting_pii/calling_llm/...", ""),
            ("model_name", "LLM model name", "NOT NULL, max 100", ""),
            ("model_version", "Model version", "max 100", ""),
            ("prompt_version", "Prompt version", "default v1, max 50", ""),
            ("temperature", "LLM temperature", "default 0.1", ""),
            ("latency_ms", "Processing latency (ms)", "", ""),
            ("input_tokens", "Input token count", "", ""),
            ("output_tokens", "Output token count", "", ""),
            ("llm_raw_json", "Raw LLM JSON output", "", ""),
            ("normalized_json", "Normalized JSON", "", ""),
            ("warnings", "Warnings list", "", ""),
            ("requirements", "Post-processing requirements", "", ""),
            ("error_code", "Error code", "max 50", ""),
            ("error_message", "Error message", "", ""),
            ("retry_count", "Retry attempts", "default 0", ""),
            ("task_started_at", "Task start time", "", ""),
            ("task_completed_at", "Task completion time", "", ""),
            ("created_at", "Creation timestamp", "default now", ""),
            ("updated_at", "Last update timestamp", "auto", ""),
        ],
    ),
    (
        "resumes_parserunstatuslog",
        "",
        [
            ("id", "Log entry ID", "NOT NULL", "PK"),
            ("parse_run_id", "Parse run ID", "NOT NULL", "FK → resumes_parserun"),
            ("old_status", "Previous status", "max 20", ""),
            ("new_status", "New status", "NOT NULL, max 20", ""),
            ("changed_at", "Change timestamp", "auto", ""),
            ("reason", "Change reason", "", ""),
        ],
    ),
    (
        "candidates_candidate",
        "",
        [
            ("id", "Candidate ID", "NOT NULL", "PK"),
            ("resume_document_id", "Resume document ID", "NOT NULL", "FK → resumes_resumedocument"),
            ("parse_run_id", "Parse run ID", "NOT NULL", "FK → resumes_parserun"),
            ("full_name", "Full name", "max 255", ""),
            ("location", "Location", "max 255", ""),
            ("headline", "Professional headline", "max 255", ""),
            ("primary_email", "Primary email", "max 255", ""),
            ("primary_phone", "Primary phone", "max 50", ""),
            ("linkedin", "LinkedIn URL", "max 255", ""),
            ("github", "GitHub URL", "max 255", ""),
            ("portfolio", "Portfolio URL", "max 255", ""),
            ("primary_role", "Primary role", "max 100", ""),
            ("seniority", "Seniority level", "max 50", ""),
            ("overall_confidence", "Overall confidence score", "default 0.0", ""),
            ("summary_one_liner", "One-line summary", "", ""),
            ("summary_highlights", "Summary highlights (JSON)", "", ""),
            ("created_at", "Creation timestamp", "default now", ""),
            ("updated_at", "Last update timestamp", "auto", ""),
        ],
    ),
    (
        "candidates_skill",
        "",
        [
            ("id", "Skill ID", "NOT NULL", "PK"),
            ("candidate_id", "Candidate ID", "NOT NULL", "FK → candidates_candidate"),
            ("name", "Skill name", "NOT NULL, max 100", ""),
            ("category", "Skill category", "max 100", ""),
            ("confidence", "Confidence score", "default 0.0", ""),
            ("evidence", "Supporting evidence (JSON)", "", ""),
        ],
    ),
    (
        "candidates_educationentry",
        "",
        [
            ("id", "Entry ID", "NOT NULL", "PK"),
            ("candidate_id", "Candidate ID", "NOT NULL", "FK → candidates_candidate"),
            ("institution", "Institution name", "max 255", ""),
            ("degree", "Degree", "max 255", ""),
            ("field_of_study", "Field of study", "max 255", ""),
            ("start_date", "Start date", "max 10", ""),
            ("end_date", "End date", "max 10", ""),
            ("grade", "Grade", "max 50", ""),
            ("confidence", "Confidence score", "default 0.0", ""),
            ("evidence", "Supporting evidence (JSON)", "", ""),
        ],
    ),
    (
        "candidates_experienceentry",
        "",
        [
            ("id", "Entry ID", "NOT NULL", "PK"),
            ("candidate_id", "Candidate ID", "NOT NULL", "FK → candidates_candidate"),
            ("company", "Company name", "max 255", ""),
            ("title", "Job title", "max 255", ""),
            ("employment_type", "Employment type", "max 50", ""),
            ("start_date", "Start date", "max 10", ""),
            ("end_date", "End date", "max 10", ""),
            ("is_current", "Current job flag", "default false", ""),
            ("location", "Location", "max 255", ""),
            ("bullets", "Bullet points (JSON)", "", ""),
            ("technologies", "Technologies (JSON)", "", ""),
            ("confidence", "Confidence score", "default 0.0", ""),
            ("evidence", "Supporting evidence (JSON)", "", ""),
        ],
    ),
    (
        "candidates_candidateeditlog",
        "",
        [
            ("id", "Log entry ID", "NOT NULL", "PK"),
            ("candidate_id", "Candidate ID", "NOT NULL", "FK → candidates_candidate"),
            ("edited_by_id", "User who edited", "", "FK → auth_user"),
            ("edited_at", "Edit timestamp", "default now", ""),
            ("changes", "Field-level diffs (JSON)", "NOT NULL", ""),
            ("before_snapshot", "State before edit (JSON)", "", ""),
            ("after_snapshot", "State after edit (JSON)", "", ""),
        ],
    ),
]


def main():
    output_path = "docs/database_schema.pdf"
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        name="TableHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
    )
    sub_style = ParagraphStyle(
        name="SubHeading",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=8,
    )

    story = []
    story.append(Paragraph("Resume Parse Pro AI — Database Schema", title_style))
    story.append(Paragraph(
        "Complete reference of all tables, columns, constraints, and relationships.",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.25 * inch))

    for table_name, subtitle, rows in TABLES:
        story.append(Paragraph(table_name, heading_style))
        if subtitle:
            story.append(Paragraph(subtitle, sub_style))

        # Build table: Column | Description | Constraints | PK / FK
        table_data = [
            ["Column", "Description", "Constraints", "PK / FK"],
            *rows,
        ]
        col_widths = [1.5 * inch, 2.2 * inch, 2.0 * inch, 1.3 * inch]
        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    main()
