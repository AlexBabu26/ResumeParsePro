# resumes/tests/test_utils.py
from django.test import SimpleTestCase
from resumes.utils import parse_json_safely


class ParseJsonSafelyTests(SimpleTestCase):
    def test_parses_plain_json(self):
        out = parse_json_safely('{"a": 1}')
        self.assertEqual(out["a"], 1)

    def test_parses_json_in_code_fence(self):
        text = "```json\n{\"a\": 2}\n```"
        out = parse_json_safely(text)
        self.assertEqual(out["a"], 2)

    def test_parses_json_with_preamble_and_trailing_text(self):
        text = "Here you go:\n{\"a\": 3, \"b\": \"x\"}\nThanks!"
        out = parse_json_safely(text)
        self.assertEqual(out["a"], 3)
        self.assertEqual(out["b"], "x")

