# candidates/admin.py
from django.contrib import admin
from .models import Candidate, Skill, EducationEntry, ExperienceEntry, CandidateEditLog


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0
    fields = ("name", "category", "confidence")
    readonly_fields = ()
    show_change_link = True


class EducationInline(admin.TabularInline):
    model = EducationEntry
    extra = 0
    fields = ("institution", "degree", "field_of_study", "start_date", "end_date", "confidence")
    show_change_link = True


class ExperienceInline(admin.TabularInline):
    model = ExperienceEntry
    extra = 0
    fields = ("company", "title", "start_date", "end_date", "is_current", "confidence")
    show_change_link = True


class EditLogInline(admin.TabularInline):
    model = CandidateEditLog
    extra = 0
    fields = ("id", "edited_by", "edited_at")
    readonly_fields = ("id", "edited_by", "edited_at")
    can_delete = False
    show_change_link = True


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "primary_role",
        "seniority",
        "overall_confidence",
        "uploaded_by",
        "created_at",
    )
    list_filter = ("primary_role", "seniority", "created_at")
    search_fields = ("full_name", "primary_email", "primary_phone", "primary_role", "headline", "location")
    readonly_fields = ("overall_confidence", "created_at")

    inlines = [SkillInline, EducationInline, ExperienceInline, EditLogInline]

    def uploaded_by(self, obj):
        # via resume_document FK
        u = getattr(obj.resume_document, "uploaded_by", None)
        return u.username if u else None
    uploaded_by.short_description = "uploaded_by"


@admin.register(CandidateEditLog)
class CandidateEditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "edited_by", "edited_at")
    list_filter = ("edited_at",)
    search_fields = ("candidate__full_name", "edited_by__username", "edited_by__email")
    readonly_fields = ("edited_at",)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "name", "category", "confidence")
    list_filter = ("category",)
    search_fields = ("name", "candidate__full_name")


@admin.register(EducationEntry)
class EducationEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "institution", "degree", "start_date", "end_date", "confidence")
    search_fields = ("institution", "degree", "candidate__full_name")


@admin.register(ExperienceEntry)
class ExperienceEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "company", "title", "start_date", "end_date", "is_current", "confidence")
    search_fields = ("company", "title", "candidate__full_name")
