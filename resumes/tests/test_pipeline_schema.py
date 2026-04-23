# resumes/tests/test_pipeline_schema.py
from django.test import SimpleTestCase
from resumes.pipeline import validate_against_schema, normalize_and_validate, extract_known_pii


class PipelineSchemaValidationTests(SimpleTestCase):
    def test_validate_against_schema_returns_errors(self):
        bad = {"schema_version": "1.0"}  # missing required keys
        errors = validate_against_schema(bad)
        self.assertTrue(errors)  # should have at least one error

    def test_normalize_and_validate_marks_schema_failure_warning(self):
        raw_text = "John Doe\njohn@example.com\n"
        known = extract_known_pii(raw_text)

        bad = {"schema_version": "1.0"}  # missing required structure
        norm, warnings, missing, status = normalize_and_validate(bad, raw_text, known)

        self.assertIn("jsonschema_validation_failed", warnings)
        self.assertIn("candidate.full_name", missing)
        self.assertIn(status, ["partial", "failed"])
        self.assertIn("candidate", norm)  # still returns canonical-shaped output

    def test_string_skills_produce_objects_without_skill_schema_spam(self):
        """LLM string[] skills are coerced before validation; input dict is not mutated."""
        raw_text = "John\njohn@example.com\n"
        known = extract_known_pii(raw_text)
        llm = {
            "schema_version": "1.0",
            "candidate": {
                "full_name": "John",
                "emails": ["john@example.com"],
                "phones": [],
                "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
            },
            "skills": ["Python", "Django"],
            "education": [],
            "experience": [],
            "quality": {
                "warnings": [],
                "missing_critical_fields": [],
                "overall_confidence": 0.0,
            },
        }
        norm, warnings, missing, _status = normalize_and_validate(llm, raw_text, known)
        self.assertIsInstance(norm["skills"][0], dict)
        self.assertEqual(norm["skills"][0]["name"], "Python")
        self.assertEqual(llm["skills"], ["Python", "Django"])
        skill_type_msgs = [w for w in warnings if w.startswith("skills.") and "not of type" in w]
        self.assertEqual(skill_type_msgs, [])

