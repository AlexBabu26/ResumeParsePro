# resumes/tests/test_upload_idempotency_and_ownership.py
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APIClient

from resumes.models import ResumeDocument, ParseRun
from resumes.services import persist_candidate_from_normalized
from candidates.models import Candidate


def make_docx_bytes(text: str) -> bytes:
    import docx
    buf = BytesIO()
    d = docx.Document()
    d.add_paragraph(text)
    d.save(buf)
    return buf.getvalue()


def dummy_parse_task(run_id: int):
    """
    Replaces Celery task parse_resume_parse_run in tests to avoid network calls.
    It marks the run success and persists a minimal Candidate.
    """
    run = ParseRun.objects.select_related("resume_document").get(id=run_id)
    doc = run.resume_document

    normalized = {
        "schema_version": "1.0",
        "candidate": {
            "full_name": "John Doe",
            "headline": "Software Engineer",
            "location": "Dubai",
            "emails": ["john@example.com"],
            "phones": [],
            "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
        },
        "skills": [{"name": "Python", "category": "Programming", "confidence": 0.9, "evidence": []}],
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "classification": {
            "primary_role": "Software Engineer",
            "secondary_roles": [],
            "seniority": "Mid",
            "confidence": 0.8,
            "rationale": "Based on headline and skills",
        },
        "summary": {"one_liner": "Python developer.", "highlights": ["Built APIs"]},
        "quality": {"warnings": [], "missing_critical_fields": [], "overall_confidence": 0.8},
    }

    run.status = "success"
    run.llm_raw_json = {}
    run.normalized_json = normalized
    run.save(update_fields=["status", "llm_raw_json", "normalized_json"])

    persist_candidate_from_normalized(doc, run, normalized)


@override_settings(RESUME_PARSE_ASYNC=True)  # we still call sync=1 in request
class UploadIdempotencyAndOwnershipTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="u1", password="pass12345")
        self.user2 = User.objects.create_user(username="u2", password="pass12345")
        self.client = APIClient()

    @patch("resumes.views.parse_resume_parse_run", side_effect=dummy_parse_task)
    def test_upload_and_duplicate_detection(self, _patched):
        self.client.force_authenticate(user=self.user1)

        docx_bytes = make_docx_bytes("John Doe\njohn@example.com\nPython\n")
        f1 = SimpleUploadedFile("resume.docx", docx_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        # First upload (sync)
        r1 = self.client.post("/api/v1/resumes/upload/?sync=1", data={"file": f1}, format="multipart")
        self.assertIn(r1.status_code, [201])
        self.assertTrue(r1.data["success"])
        data1 = r1.data["data"]
        self.assertIsNotNone(data1["resume_document_id"])
        self.assertIsNotNone(data1["parse_run_id"])
        self.assertIsNotNone(data1["candidate_id"])

        self.assertEqual(ResumeDocument.objects.count(), 1)
        self.assertEqual(Candidate.objects.count(), 1)

        # Second upload with same bytes (duplicate)
        f2 = SimpleUploadedFile("resume.docx", docx_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        r2 = self.client.post("/api/v1/resumes/upload/?sync=1", data={"file": f2}, format="multipart")
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.data["success"])
        self.assertTrue(r2.data["data"]["duplicate"])
        self.assertEqual(ResumeDocument.objects.count(), 1)  # still 1
        self.assertEqual(Candidate.objects.count(), 1)       # still 1 (no new parse)

    @patch("resumes.views.parse_resume_parse_run", side_effect=dummy_parse_task)
    def test_ownership_filtering(self, _patched):
        # user1 uploads
        self.client.force_authenticate(user=self.user1)
        docx_bytes = make_docx_bytes("John Doe\njohn@example.com\nPython\n")
        f1 = SimpleUploadedFile("resume.docx", docx_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.client.post("/api/v1/resumes/upload/?sync=1", data={"file": f1}, format="multipart")

        # user2 lists candidates -> should see none
        self.client.force_authenticate(user=self.user2)
        r = self.client.get("/api/v1/candidates/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["success"])
        self.assertEqual(r.data["data"]["count"], 0)

        # user2 lists resume-documents -> should see none
        r2 = self.client.get("/api/v1/resume-documents/")
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.data["success"])
        self.assertEqual(r2.data["data"]["count"], 0)

