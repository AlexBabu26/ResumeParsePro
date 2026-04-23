"""Persistence coerces string-shaped LLM output (e.g. skills: ['Python', ...]) into rows."""
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase

from candidates.models import Candidate, Skill, EducationEntry, ExperienceEntry
from resumes.models import ParseRun, ResumeDocument
from resumes.services import persist_candidate_from_normalized


class PersistStringShapesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="t", password="p")
        self.doc = ResumeDocument.objects.create(
            original_filename="r.pdf",
            file=ContentFile(b"dummy", name="r.pdf"),
            mime_type="application/pdf",
            uploaded_by=self.user,
        )
        self.run = ParseRun.objects.create(
            resume_document=self.doc,
            status="success",
            model_name="test",
        )

    def test_string_skills_and_education_persisted(self):
        normalized = {
            "candidate": {
                "full_name": "Test",
                "emails": ["a@a.com"],
                "phones": [],
                "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
            },
            "skills": ["Python", "Django"],
            "education": ["MSc in CS"],
            "experience": [
                "Engineer | Acme",
                "2020-01-01 - 2021-12-31",
            ],
            "quality": {"overall_confidence": 0.5},
            "summary": {"one_liner": None, "highlights": []},
            "classification": {"primary_role": None, "seniority": None},
        }
        persist_candidate_from_normalized(self.doc, self.run, normalized)
        c = Candidate.objects.get(parse_run=self.run)
        self.assertEqual(Skill.objects.filter(candidate=c).count(), 2)
        self.assertEqual(
            set(Skill.objects.filter(candidate=c).values_list("name", flat=True)),
            {"Python", "Django"},
        )
        self.assertEqual(EducationEntry.objects.filter(candidate=c).count(), 1)
        ex = ExperienceEntry.objects.filter(candidate=c).first()
        self.assertIsNotNone(ex)
        self.assertEqual(ex.title, "Engineer")
        self.assertEqual(ex.company, "Acme")
        self.assertEqual(ex.bullets, ["2020-01-01 - 2021-12-31"])
