from django.db import models
from django.utils import timezone


class ResumeDocument(models.Model):
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="resumes/")
    mime_type = models.CharField(max_length=100)
    file_hash = models.CharField(max_length=64, db_index=True, blank=True, default='')  # SHA256 hex
    file_size = models.BigIntegerField(default=0)

    raw_text = models.TextField(null=True, blank=True)
    extraction_method = models.CharField(max_length=50, null=True, blank=True)

    uploaded_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_resumes"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["uploaded_by", "file_hash"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["uploaded_by", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.id} - {self.original_filename}"


class ParseRun(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("success", "Success"),
        ("partial", "Partial"),
        ("failed", "Failed"),
        ("rejected", "Rejected"),
    ]

    PROGRESS_STAGE_CHOICES = [
        ("queued", "Queued"),
        ("extracting_pii", "Extracting PII"),
        ("calling_llm", "Calling LLM"),
        ("validating", "Validating"),
        ("classifying", "Classifying"),
        ("summarizing", "Summarizing"),
        ("persisting", "Persisting"),
        ("complete", "Complete"),
    ]

    resume_document = models.ForeignKey(ResumeDocument, on_delete=models.CASCADE, related_name="parse_runs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    progress_stage = models.CharField(max_length=20, choices=PROGRESS_STAGE_CHOICES, default="queued")

    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=100, null=True, blank=True)
    prompt_version = models.CharField(max_length=50, default="v1")

    temperature = models.FloatField(default=0.1)
    latency_ms = models.IntegerField(null=True, blank=True)

    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)

    llm_raw_json = models.JSONField(null=True, blank=True)
    normalized_json = models.JSONField(null=True, blank=True)

    warnings = models.JSONField(null=True, blank=True)
    requirements = models.JSONField(null=True, blank=True)  # Requirements to check after processing
    error_code = models.CharField(max_length=50, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    # Task tracking fields
    retry_count = models.IntegerField(default=0)
    task_started_at = models.DateTimeField(null=True, blank=True)
    task_completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["resume_document", "status"]),
            models.Index(fields=["resume_document", "-created_at"]),
        ]

    def __str__(self):
        return f"ParseRun {self.id} ({self.status})"


class ParseRunStatusLog(models.Model):
    """
    Audit log for ParseRun status changes.
    Tracks each status transition for debugging and analytics.
    """
    parse_run = models.ForeignKey(ParseRun, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["parse_run", "-changed_at"]),
        ]

    def __str__(self):
        return f"StatusLog {self.id}: {self.old_status} -> {self.new_status}"

