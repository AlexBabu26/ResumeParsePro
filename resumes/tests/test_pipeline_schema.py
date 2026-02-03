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

