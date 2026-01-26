# candidates/tests/test_audit_export.py
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APIClient

from candidates.models import CandidateEditLog, Candidate
from resumes.models import ParseRun
from resumes.services import persist_candidate_from_normalized


def make_docx_bytes(text: str) -> bytes:
    import docx
    buf = BytesIO()
    d = docx.Document()
    d.add_paragraph(text)
    d.save(buf)
    return buf.getvalue()


def dummy_parse_task(run_id: int):
    run = ParseRun.objects.select_related("resume_document").get(id=run_id)
    doc = run.resume_document

    normalized = {
        "schema_version": "1.0",
        "candidate": {
            "full_name": "Jane Smith",
            "headline": "Backend Developer",
            "location": "Dubai",
            "emails": ["jane@example.com"],
            "phones": [],
            "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
        },
        "skills": [{"name": "Django", "category": "Framework", "confidence": 0.9, "evidence": []}],
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "classification": {"primary_role": "Backend Engineer", "secondary_roles": [], "seniority": "Junior", "confidence": 0.7, "rationale": None},
        "summary": {"one_liner": "Django developer.", "highlights": ["Built REST APIs"]},
        "quality": {"warnings": [], "missing_critical_fields": [], "overall_confidence": 0.7},
    }

    run.status = "success"
    run.normalized_json = normalized
    run.llm_raw_json = {}
    run.save(update_fields=["status", "normalized_json", "llm_raw_json"])
    persist_candidate_from_normalized(doc, run, normalized)


@override_settings(RESUME_PARSE_ASYNC=True)
class CandidateAuditAndExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch("resumes.views.parse_resume_parse_run", side_effect=dummy_parse_task)
    def test_patch_creates_audit_log_and_export_csv(self, _patched):
        # Upload a resume to create a candidate
        docx_bytes = make_docx_bytes("Jane Smith\njane@example.com\nDjango\n")
        f1 = SimpleUploadedFile("resume.docx", docx_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        r1 = self.client.post("/api/v1/resumes/upload/?sync=1", data={"file": f1}, format="multipart")
        self.assertEqual(r1.status_code, 201)
        candidate_id = r1.data["data"]["candidate_id"]
        self.assertIsNotNone(candidate_id)

        # PATCH candidate -> should create edit log
        patch_resp = self.client.patch(f"/api/v1/candidates/{candidate_id}/", data={"headline": "Updated Headline"}, format="json")
        self.assertEqual(patch_resp.status_code, 200)
        self.assertTrue(patch_resp.data["success"])

        self.assertEqual(CandidateEditLog.objects.count(), 1)
        log = CandidateEditLog.objects.first()
        self.assertIn("headline", log.changes)
        self.assertEqual(log.changes["headline"]["to"], "Updated Headline")

        # Retrieve logs endpoint
        logs_resp = self.client.get(f"/api/v1/candidates/{candidate_id}/edit-logs/")
        self.assertEqual(logs_resp.status_code, 200)
        self.assertTrue(logs_resp.data["success"])
        self.assertEqual(len(logs_resp.data["data"]), 1)

        # CSV export
        export_resp = self.client.get("/api/v1/candidates/export/")
        self.assertEqual(export_resp.status_code, 200)
        self.assertEqual(export_resp["Content-Type"], "text/csv")
        content = export_resp.content.decode("utf-8")
        self.assertIn("full_name", content)
        self.assertIn("Jane Smith", content)

