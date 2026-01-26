# resumes/admin.py
from django.contrib import admin
from .models import ResumeDocument, ParseRun


class ParseRunInline(admin.TabularInline):
    model = ParseRun
    extra = 0
    fields = (
        "id",
        "status",
        "model_name",
        "prompt_version",
        "temperature",
        "latency_ms",
        "error_code",
        "created_at",
    )
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.register(ResumeDocument)
class ResumeDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_filename",
        "uploaded_by",
        "mime_type",
        "file_size",
        "file_hash_short",
        "extraction_method",
        "created_at",
    )
    list_filter = ("mime_type", "extraction_method", "created_at")
    search_fields = ("original_filename", "file_hash", "uploaded_by__username", "uploaded_by__email")
    readonly_fields = ("file_hash", "file_size", "created_at")
    inlines = [ParseRunInline]

    def file_hash_short(self, obj):
        return (obj.file_hash or "")[:12]
    file_hash_short.short_description = "file_hash"


@admin.register(ParseRun)
class ParseRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "resume_document",
        "status",
        "model_name",
        "prompt_version",
        "temperature",
        "latency_ms",
        "error_code",
        "created_at",
    )
    list_filter = ("status", "model_name", "created_at")
    search_fields = (
        "resume_document__original_filename",
        "resume_document__file_hash",
        "error_code",
        "error_message",
    )
    readonly_fields = (
        "created_at",
        "latency_ms",
        "input_tokens",
        "output_tokens",
    )
