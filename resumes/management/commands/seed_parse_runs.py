"""
Create demo ResumeDocument and ParseRun records for the test user so they appear
on the Parse Runs page at /resumes/parse-runs/.
"""
import hashlib
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from resumes.models import ResumeDocument, ParseRun

User = get_user_model()

# Minimal valid PDF bytes for demo files
MINIMAL_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >> endobj\nxref\n0 1\ntrailer << /Root 1 0 R >>\nstartxref\n%%EOF"


def make_doc_file(name: str, content: bytes = MINIMAL_PDF):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


class Command(BaseCommand):
    help = "Create demo parse run records for user 'test' (password: test@123)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of parse runs to create (default: 5).",
        )
        parser.add_argument(
            "--username",
            default="test",
            help="Username to assign as uploaded_by (default: test).",
        )

    def handle(self, *args, **options):
        count = options["count"]
        username = options["username"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User '{username}' does not exist. Create it first (e.g. createsuperuser or signup)."))
            return

        created = 0
        statuses = ["success", "failed", "queued", "processing", "partial"]

        for i in range(count):
            status = statuses[i % len(statuses)]
            filename = f"demo-resume-parse-run-{i + 1}.pdf"
            content = MINIMAL_PDF + f"\n% Demo {i + 1}\n".encode()
            file_hash = hashlib.sha256(content).hexdigest()

            doc = ResumeDocument(
                original_filename=filename,
                file=make_doc_file(filename, content),
                mime_type="application/pdf",
                file_hash=file_hash,
                file_size=len(content),
                uploaded_by=user,
            )
            doc.save()

            run = ParseRun.objects.create(
                resume_document=doc,
                status=status,
                progress_stage="complete" if status in ("success", "partial", "failed") else ("queued" if status == "queued" else "calling_llm"),
                model_name="openai/gpt-4o-mini",
                model_version="2024",
                prompt_version="v1",
                temperature=0.1,
                latency_ms=1200 + i * 100 if status == "success" else None,
                input_tokens=500 + i * 10 if status == "success" else None,
                output_tokens=300 + i * 5 if status == "success" else None,
                error_message="Demo failed run." if status == "failed" else None,
            )
            created += 1
            self.stdout.write(f"  Created ParseRun {run.id} (doc: {doc.original_filename}, status={status})")

        self.stdout.write(self.style.SUCCESS(f"Created {created} parse run(s) for user '{username}'. Open http://127.0.0.1:7000/resumes/parse-runs/ (logged in as {username}) to see them."))
