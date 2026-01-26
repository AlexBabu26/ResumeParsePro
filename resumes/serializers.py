from rest_framework import serializers
from .models import ResumeDocument, ParseRun


class ResumeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeDocument
        fields = (
            "id",
            "original_filename",
            "file",
            "mime_type",
            "file_hash",
            "file_size",
            "raw_text",
            "extraction_method",
            "uploaded_by",
            "created_at",
        )
        read_only_fields = (
            "file_hash",
            "file_size",
            "raw_text",
            "extraction_method",
            "uploaded_by",
            "created_at",
        )


class ResumeUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, f):
        name = (f.name or "").lower()
        if not (name.endswith(".pdf") or name.endswith(".docx") or name.endswith(".doc")):
            raise serializers.ValidationError("Unsupported file type. Upload PDF or DOCX.")
        return f


class BulkResumeUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        min_length=1,
        max_length=100  # Limit to prevent abuse
    )
    requirements = serializers.JSONField(required=False, allow_null=True)

    def validate_files(self, files):
        validated_files = []
        for f in files:
            name = (f.name or "").lower()
            if not (name.endswith(".pdf") or name.endswith(".docx") or name.endswith(".doc")):
                raise serializers.ValidationError(
                    f"Unsupported file type for '{f.name}'. Only PDF and DOCX files are supported."
                )
            validated_files.append(f)
        return validated_files

    def validate_requirements(self, value):
        """Validate requirements structure"""
        if value is None:
            return None
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Requirements must be a JSON object.")
        
        allowed_keys = {
            "required_skills",  # List of skill names (all must be present)
            "any_skills",  # List of skill names (at least one must be present)
            "min_years_experience",  # Minimum years of experience (float)
            "required_education_degree",  # List of degree types (e.g., ["Bachelor", "Master"])
            "required_primary_role",  # List of roles (e.g., ["Software Engineer", "Developer"])
            "required_seniority",  # List of seniority levels (e.g., ["Senior", "Lead"])
            "location_contains",  # String that location must contain
            "min_confidence",  # Minimum overall_confidence (float 0-1)
            "use_llm_validation",  # Boolean - use LLM for semantic validation (default: True)
        }
        
        for key in value.keys():
            if key not in allowed_keys:
                raise serializers.ValidationError(
                    f"Unknown requirement key: '{key}'. Allowed keys: {', '.join(allowed_keys)}"
                )
        
        # Validate specific requirement types
        if "min_years_experience" in value:
            if not isinstance(value["min_years_experience"], (int, float)) or value["min_years_experience"] < 0:
                raise serializers.ValidationError("min_years_experience must be a non-negative number.")
        
        if "min_confidence" in value:
            if not isinstance(value["min_confidence"], (int, float)) or not (0 <= value["min_confidence"] <= 1):
                raise serializers.ValidationError("min_confidence must be a number between 0 and 1.")
        
        for list_key in ["required_skills", "any_skills", "required_education_degree", "required_primary_role", "required_seniority"]:
            if list_key in value and not isinstance(value[list_key], list):
                raise serializers.ValidationError(f"{list_key} must be a list.")
        
        if "location_contains" in value and not isinstance(value["location_contains"], str):
            raise serializers.ValidationError("location_contains must be a string.")
        
        return value


class ParseRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParseRun
        fields = (
            "id",
            "resume_document",
            "status",
            "model_name",
            "model_version",
            "prompt_version",
            "temperature",
            "latency_ms",
            "input_tokens",
            "output_tokens",
            "llm_raw_json",
            "normalized_json",
            "warnings",
            "requirements",
            "error_code",
            "error_message",
            "created_at",
        )
        read_only_fields = fields

