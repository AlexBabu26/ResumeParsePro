"""
Retry all failed parse runs with the new API key.
This is useful after updating your OPENROUTER_API_KEY.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from resumes.models import ParseRun
from resumes.tasks import parse_resume_parse_run

print("=" * 70)
print("Parse Pro AI - Retry Failed Parse Runs")
print("=" * 70)
print()

# Find all failed parse runs with AUTH_ERROR
failed_runs = ParseRun.objects.filter(
    status='failed',
    error_code='AUTH_ERROR'
).select_related('resume_document').order_by('-created_at')

count = failed_runs.count()

if count == 0:
    print("[INFO] No failed parse runs with AUTH_ERROR found.")
    print("       All your parse runs are in good shape!")
    exit(0)

print(f"[INFO] Found {count} failed parse run(s) with AUTH_ERROR")
print("-" * 70)

for run in failed_runs:
    doc = run.resume_document
    print(f"\nParse Run #{run.id}")
    print(f"  File: {doc.original_filename}")
    print(f"  Created: {run.created_at}")
    print(f"  Error: {run.error_message}")

print()
print("-" * 70)
response = input(f"\nRetry all {count} failed parse run(s) with the new API key? (y/N): ")

if response.lower() != 'y':
    print("[INFO] Cancelled. No parse runs were retried.")
    exit(0)

print()
print("[INFO] Retrying parse runs...")
print("-" * 70)

retried = 0
for run in failed_runs:
    doc = run.resume_document
    
    # Create a new parse run
    from django.conf import settings
    new_run = ParseRun.objects.create(
        resume_document=doc,
        status="queued",
        model_name=getattr(settings, "OPENROUTER_EXTRACT_MODEL", "qwen/qwen3-next-80b-a3b-instruct:free"),
        prompt_version="v1",
        temperature=float(getattr(settings, "OPENROUTER_TEMPERATURE", 0.1)),
    )
    
    # Queue the task
    if getattr(settings, "RESUME_PARSE_ASYNC", True):
        parse_resume_parse_run.delay(new_run.id)
        print(f"[OK] Parse Run #{run.id} -> New Run #{new_run.id} (queued)")
    else:
        parse_resume_parse_run(new_run.id)
        new_run.refresh_from_db()
        print(f"[OK] Parse Run #{run.id} -> New Run #{new_run.id} (status: {new_run.status})")
    
    retried += 1

print()
print("=" * 70)
print(f"[OK] Successfully retried {retried} parse run(s)!")
print("=" * 70)
print()
print("Next steps:")
print("  1. Check Parse Runs page: http://localhost:8000/resumes/parse-runs/")
print("  2. Check Candidates page: http://localhost:8000/candidates/")
print()
