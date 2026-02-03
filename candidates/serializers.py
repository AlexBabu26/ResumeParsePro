from rest_framework import serializers
from .models import Candidate, Skill, EducationEntry, ExperienceEntry, CandidateEditLog


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("id", "name", "category", "confidence", "evidence")


class EducationEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationEntry
        fields = (
            "id",
            "institution",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "grade",
            "confidence",
            "evidence",
        )


class ExperienceEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperienceEntry
        fields = (
            "id",
            "company",
            "title",
            "employment_type",
            "start_date",
            "end_date",
            "is_current",
            "location",
            "bullets",
            "technologies",
            "confidence",
            "evidence",
        )


class CandidateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = (
            "id",
            "full_name",
            "headline",
            "location",
            "primary_email",
            "primary_phone",
            "primary_role",
            "seniority",
            "overall_confidence",
            "created_at",
        )


class CandidateDetailSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    education = EducationEntrySerializer(many=True, read_only=True)
    experience = ExperienceEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = (
            "id",
            "resume_document",
            "parse_run",
            "full_name",
            "headline",
            "location",
            "primary_email",
            "primary_phone",
            "linkedin",
            "github",
            "portfolio",
            "primary_role",
            "seniority",
            "overall_confidence",
            "summary_one_liner",
            "summary_highlights",
            "skills",
            "education",
            "experience",
            "created_at",
        )
        read_only_fields = ("resume_document", "parse_run", "overall_confidence", "created_at")


class CandidatePatchSerializer(serializers.ModelSerializer):
    """
    Human edits: restrict what can be edited to avoid accidental overwrite
    of model-generated confidence and relational data.
    """
    class Meta:
        model = Candidate
        fields = (
            "full_name",
            "headline",
            "location",
            "primary_email",
            "primary_phone",
            "linkedin",
            "github",
            "portfolio",
            "primary_role",
            "seniority",
            "summary_one_liner",
            "summary_highlights",
        )


class CandidateEditLogSerializer(serializers.ModelSerializer):
    edited_by = serializers.SerializerMethodField()

    class Meta:
        model = CandidateEditLog
        fields = ("id", "candidate", "edited_by", "edited_at", "changes", "before_snapshot", "after_snapshot")

    def get_edited_by(self, obj):
        if not obj.edited_by:
            return None
        return {"id": obj.edited_by.id, "username": obj.edited_by.username, "email": obj.edited_by.email}
