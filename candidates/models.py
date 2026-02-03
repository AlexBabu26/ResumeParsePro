from django.db import models
from django.utils import timezone


class Candidate(models.Model):
    resume_document = models.ForeignKey("resumes.ResumeDocument", on_delete=models.CASCADE, related_name="candidate_profiles")
    parse_run = models.ForeignKey("resumes.ParseRun", on_delete=models.CASCADE, related_name="candidate_profiles")

    full_name = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    headline = models.CharField(max_length=255, null=True, blank=True)

    primary_email = models.CharField(max_length=255, null=True, blank=True)
    primary_phone = models.CharField(max_length=50, null=True, blank=True)

    linkedin = models.CharField(max_length=255, null=True, blank=True)
    github = models.CharField(max_length=255, null=True, blank=True)
    portfolio = models.CharField(max_length=255, null=True, blank=True)

    primary_role = models.CharField(max_length=100, null=True, blank=True)
    seniority = models.CharField(max_length=50, null=True, blank=True)

    overall_confidence = models.FloatField(default=0.0)

    summary_one_liner = models.TextField(null=True, blank=True)
    summary_highlights = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["primary_role"]),
            models.Index(fields=["overall_confidence"]),
            models.Index(fields=["seniority"]),
            models.Index(fields=["resume_document", "-created_at"]),
            models.Index(fields=["parse_run", "-created_at"]),
        ]

    def __str__(self):
        return self.full_name or f"Candidate {self.id}"


class Skill(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100, null=True, blank=True)
    confidence = models.FloatField(default=0.0)
    evidence = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["candidate", "name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.candidate_id})"


class EducationEntry(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="education")
    institution = models.CharField(max_length=255, null=True, blank=True)
    degree = models.CharField(max_length=255, null=True, blank=True)
    field_of_study = models.CharField(max_length=255, null=True, blank=True)
    start_date = models.CharField(max_length=10, null=True, blank=True)
    end_date = models.CharField(max_length=10, null=True, blank=True)
    grade = models.CharField(max_length=50, null=True, blank=True)
    confidence = models.FloatField(default=0.0)
    evidence = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["institution"]),
            models.Index(fields=["degree"]),
        ]


class ExperienceEntry(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="experience")
    company = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    employment_type = models.CharField(max_length=50, null=True, blank=True)
    start_date = models.CharField(max_length=10, null=True, blank=True)
    end_date = models.CharField(max_length=10, null=True, blank=True)
    is_current = models.BooleanField(default=False)
    location = models.CharField(max_length=255, null=True, blank=True)

    bullets = models.JSONField(null=True, blank=True)
    technologies = models.JSONField(null=True, blank=True)

    confidence = models.FloatField(default=0.0)
    evidence = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["title"]),
            models.Index(fields=["is_current"]),
            models.Index(fields=["candidate", "is_current", "-start_date"]),
        ]


class CandidateEditLog(models.Model):
    """
    Audit log for human edits (PATCH) to Candidate fields.
    Stores field-level diffs and before/after snapshots for traceability.
    """
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="edit_logs")
    edited_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="candidate_edits")
    edited_at = models.DateTimeField(default=timezone.now)

    # { "field": { "from": old, "to": new }, ... }
    changes = models.JSONField()

    # Optional full snapshots (useful in demos/evaluations)
    before_snapshot = models.JSONField(null=True, blank=True)
    after_snapshot = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["-edited_at"]),
            models.Index(fields=["candidate", "-edited_at"]),
        ]

    def __str__(self):
        return f"EditLog {self.id} Candidate {self.candidate_id}"

