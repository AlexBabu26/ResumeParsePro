from resumes.models import ParseRun

runs = ParseRun.objects.all().order_by('id')
print(f'Total ParseRuns: {runs.count()}\n')

for r in runs:
    filename = r.resume_document.original_filename if r.resume_document else "N/A"
    print(f'ID: {r.id}')
    print(f'  Status: {r.status}')
    print(f'  File: {filename}')
    print(f'  Requirements: {r.requirements}')
    print()
