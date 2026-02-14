from rest_framework import serializers
from .models import ResumeDocument, ParseRun


# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Supported file extensions
SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.txt']


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
    """
    Single resume file upload serializer with user-friendly validation.
    """
    file = serializers.FileField(
        error_messages={
            'required': 'Please select a resume file to upload.',
            'empty': 'The file you selected appears to be empty. Please choose a different file.',
            'invalid': 'There was a problem with the uploaded file. Please try again.',
        }
    )

    def validate_file(self, f):
        # Check file size
        if hasattr(f, 'size') and f.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"This file is too large ({f.size // (1024*1024)}MB). "
                f"Please upload a file smaller than 10MB."
            )
        
        # Check file extension
        name = (f.name or "").lower()
        if not any(name.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            raise serializers.ValidationError(
                "This file type is not supported. Please upload a PDF, Word document (.docx), "
                "or plain text file (.txt)."
            )
        
        # Check for empty filename
        if not f.name or not f.name.strip():
            raise serializers.ValidationError("The file must have a name.")
        
        return f


class BulkResumeUploadSerializer(serializers.Serializer):
    """
    Bulk resume upload serializer with comprehensive validation and user-friendly messages.
    """
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        min_length=1,
        max_length=100,
        error_messages={
            'empty': 'Please select at least one resume file to upload.',
            'min_length': 'Please select at least one resume file to upload.',
            'max_length': 'You can upload a maximum of 100 files at once. Please split your upload into smaller batches.',
        }
    )
    requirements = serializers.JSONField(required=False, allow_null=True)

    def validate_files(self, files):
        validated_files = []
        errors = []
        
        for f in files:
            # Check file size
            if hasattr(f, 'size') and f.size > MAX_FILE_SIZE:
                errors.append(
                    f"'{f.name}' is too large ({f.size // (1024*1024)}MB). Maximum size is 10MB."
                )
                continue
            
            # Check file extension
            name = (f.name or "").lower()
            if not any(name.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                errors.append(
                    f"'{f.name}' is not a supported file type. Please use PDF, DOCX, or TXT files."
                )
                continue
            
            validated_files.append(f)
        
        if errors:
            raise serializers.ValidationError(errors)
        
        if not validated_files:
            raise serializers.ValidationError("No valid files found. Please upload PDF, DOCX, or TXT files.")
        
        return validated_files

    def validate_requirements(self, value):
        """
        Validate requirements structure with user-friendly error messages.
        
        Requirements allow you to filter candidates during upload:
        - required_skills: Skills the candidate must have
        - any_skills: At least one of these skills must be present  
        - min_years_experience: Minimum years of work experience
        - etc.
        """
        if value is None:
            return None
        
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Requirements must be provided as a JSON object. "
                "Example: {\"required_skills\": [\"Python\", \"JavaScript\"]}"
            )
        
        allowed_keys = {
            "required_skills",
            "any_skills",
            "min_years_experience",
            "required_education_degree",
            "required_primary_role",
            "required_seniority",
            "location_contains",
            "min_confidence",
            "use_llm_validation",
        }
        
        # Check for unknown keys
        unknown_keys = set(value.keys()) - allowed_keys
        if unknown_keys:
            raise serializers.ValidationError(
                f"Unknown filter option(s): {', '.join(unknown_keys)}. "
                f"Available options: {', '.join(sorted(allowed_keys))}"
            )
        
        # Validate min_years_experience
        if "min_years_experience" in value:
            years = value["min_years_experience"]
            if not isinstance(years, (int, float)):
                raise serializers.ValidationError(
                    "Minimum years of experience must be a number (e.g., 3 or 2.5)."
                )
            if years < 0:
                raise serializers.ValidationError(
                    "Minimum years of experience cannot be negative."
                )
            if years > 50:
                raise serializers.ValidationError(
                    "Minimum years of experience seems too high. Please enter a reasonable value."
                )
        
        # Validate min_confidence
        if "min_confidence" in value:
            conf = value["min_confidence"]
            if not isinstance(conf, (int, float)):
                raise serializers.ValidationError(
                    "Minimum confidence must be a number between 0 and 1 (e.g., 0.7 for 70%)."
                )
            if not (0 <= conf <= 1):
                raise serializers.ValidationError(
                    "Minimum confidence must be between 0 and 1 (e.g., 0.7 for 70% confidence)."
                )
        
        # Validate list fields
        list_fields = {
            "required_skills": "Required skills",
            "any_skills": "Skills (any of)",
            "required_education_degree": "Required education",
            "required_primary_role": "Required roles",
            "required_seniority": "Required seniority levels",
        }
        
        for field, label in list_fields.items():
            if field in value:
                if not isinstance(value[field], list):
                    raise serializers.ValidationError(
                        f"{label} must be provided as a list. "
                        f"Example: [\"{field.replace('_', ' ').title()} 1\", \"{field.replace('_', ' ').title()} 2\"]"
                    )
                if not value[field]:
                    raise serializers.ValidationError(
                        f"{label} cannot be empty. Please provide at least one value."
                    )
                # Check for non-string values
                if not all(isinstance(item, str) for item in value[field]):
                    raise serializers.ValidationError(
                        f"All items in {label.lower()} must be text values."
                    )
        
        # Validate location_contains
        if "location_contains" in value:
            loc = value["location_contains"]
            if not isinstance(loc, str):
                raise serializers.ValidationError(
                    "Location filter must be text (e.g., \"New York\" or \"Remote\")."
                )
            if not loc.strip():
                raise serializers.ValidationError(
                    "Location filter cannot be empty."
                )
        
        return value


class ParseRunSerializer(serializers.ModelSerializer):
    """
    Parse run serializer with human-readable status information.
    """
    status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ParseRun
        fields = (
            "id",
            "resume_document",
            "status",
            "status_display",
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
    
    def get_status_display(self, obj):
        """Return a human-readable status message."""
        status_messages = {
            'queued': 'Waiting to be processed',
            'processing': 'Currently being analyzed',
            'success': 'Completed successfully',
            'partial': 'Completed with some missing information',
            'failed': 'Processing failed',
        }
        return status_messages.get(obj.status, obj.status)

