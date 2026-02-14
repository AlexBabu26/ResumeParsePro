import csv
import logging
from io import StringIO

from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponse

from django_filters import rest_framework as django_filters
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.throttling import ScopedRateThrottle

from core.responses import ok, fail
from .filters import CandidateFilter
from .models import Candidate, CandidateEditLog
from .serializers import (
    CandidateListSerializer,
    CandidateDetailSerializer,
    CandidatePatchSerializer,
    CandidateEditLogSerializer,
)

logger = logging.getLogger(__name__)


EDITABLE_FIELDS = [
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
]


def _candidate_snapshot(c: Candidate) -> dict:
    return {f: getattr(c, f) for f in EDITABLE_FIELDS}


class CandidateViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CandidateFilter
    search_fields = ["full_name", "headline", "location", "primary_role"]
    ordering_fields = ["created_at", "overall_confidence", "full_name", "seniority"]
    ordering = ["-created_at"]

    # Default throttle applies; we also apply scoped throttles on specific actions.
    throttle_classes = [ScopedRateThrottle]

    def get_queryset(self):
        """
        Get queryset with ownership filtering and query optimization.
        
        Includes select_related for foreign keys and prefetch_related for 
        reverse relations to avoid N+1 queries.
        """
        # Base queryset with ownership filter
        qs = Candidate.objects.filter(
            resume_document__uploaded_by=self.request.user
        ).select_related(
            'resume_document',
            'parse_run',
        ).prefetch_related(
            'skills',
            'experience',
            'education',
        ).order_by("-created_at")

        # Legacy query parameter support (for backward compatibility)
        q = self.request.query_params.get("q")
        skill = self.request.query_params.get("skill")
        role = self.request.query_params.get("role")
        min_conf = self.request.query_params.get("min_conf")
        parse_run = self.request.query_params.get("parse_run")

        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(headline__icontains=q)
                | Q(location__icontains=q)
                | Q(primary_role__icontains=q)
                | Q(experience__company__icontains=q)
                | Q(experience__title__icontains=q)
            ).distinct()

        if role:
            qs = qs.filter(primary_role__icontains=role)

        if min_conf:
            try:
                qs = qs.filter(overall_confidence__gte=float(min_conf))
            except ValueError:
                pass

        if skill:
            qs = qs.filter(skills__name__iexact=skill).distinct()

        if parse_run:
            qs = qs.filter(parse_run_id=parse_run)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CandidateListSerializer
        if self.action in ("partial_update", "update"):
            return CandidatePatchSerializer
        return CandidateDetailSerializer

    def get_throttle_scope(self):
        # Scoped throttles for specific actions
        if self.action == "partial_update":
            return "candidate_patch"
        if self.action == "export":
            return "candidates_export"
        return "user"

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        """
        PATCH creates an audit log capturing changes.
        Only editable Candidate fields are allowed (via CandidatePatchSerializer).
        """
        candidate = self.get_object()

        before = _candidate_snapshot(candidate)

        serializer = self.get_serializer(candidate, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        candidate.refresh_from_db()
        after = _candidate_snapshot(candidate)

        # Compute diff
        changes = {}
        for f in EDITABLE_FIELDS:
            if before.get(f) != after.get(f):
                changes[f] = {"from": before.get(f), "to": after.get(f)}

        if changes:
            CandidateEditLog.objects.create(
                candidate=candidate,
                edited_by=request.user,
                changes=changes,
                before_snapshot=before,
                after_snapshot=after,
            )
            
            # Build a user-friendly message about what changed
            changed_fields = list(changes.keys())
            if len(changed_fields) == 1:
                change_msg = f"{changed_fields[0].replace('_', ' ').title()} has been updated."
            elif len(changed_fields) <= 3:
                change_msg = f"{', '.join(f.replace('_', ' ') for f in changed_fields)} have been updated."
            else:
                change_msg = f"{len(changed_fields)} fields have been updated."
        else:
            change_msg = "No changes were made."

        # Return full detail payload
        return ok(
            CandidateDetailSerializer(candidate).data,
            status=200,
            message=change_msg
        )

    @action(detail=True, methods=["get"], url_path="edit-logs")
    def edit_logs(self, request, pk=None):
        """Get the edit history for a candidate."""
        candidate = self.get_object()
        logs = candidate.edit_logs.order_by("-edited_at")
        
        return ok(
            CandidateEditLogSerializer(logs, many=True).data,
            status=200,
            message=f"Found {logs.count()} edit(s) for this candidate." if logs.exists() else "No edits have been made to this candidate yet."
        )

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """
        CSV export of current filtered candidate list.
        Respects the same filters as list: q, skill, role, min_conf, and all django-filter parameters.
        
        Enhanced to include:
        - Skills (comma-separated)
        - Experience count and summary
        - Education summary
        - LinkedIn/GitHub presence
        """
        qs = self.filter_queryset(self.get_queryset())
        
        # Annotate with counts for efficiency
        qs = qs.annotate(
            skills_count=Count('skills', distinct=True),
            experience_count=Count('experience', distinct=True),
            education_count=Count('education', distinct=True),
        )
        
        logger.info("Exporting candidates to CSV", extra={
            "user_id": request.user.id,
            "candidate_count": qs.count(),
        })

        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id",
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
            "skills",
            "skills_count",
            "experience_count",
            "education_summary",
            "summary_one_liner",
            "has_linkedin",
            "has_github",
            "created_at",
            "updated_at",
        ])

        for c in qs:
            # Get skills as comma-separated string
            skills = ", ".join([s.name for s in c.skills.all()[:10]])  # Limit to first 10
            if c.skills.count() > 10:
                skills += f" (+{c.skills.count() - 10} more)"
            
            # Get education summary (most recent degree)
            education_summary = ""
            latest_edu = c.education.order_by('-end_date').first()
            if latest_edu:
                parts = []
                if latest_edu.degree:
                    parts.append(latest_edu.degree)
                if latest_edu.field_of_study:
                    parts.append(f"in {latest_edu.field_of_study}")
                if latest_edu.institution:
                    parts.append(f"from {latest_edu.institution}")
                education_summary = " ".join(parts)
            
            writer.writerow([
                c.id,
                c.full_name or "",
                c.headline or "",
                c.location or "",
                c.primary_email or "",
                c.primary_phone or "",
                c.linkedin or "",
                c.github or "",
                c.portfolio or "",
                c.primary_role or "",
                c.seniority or "",
                c.overall_confidence,
                skills,
                getattr(c, 'skills_count', c.skills.count()),
                getattr(c, 'experience_count', c.experience.count()),
                education_summary,
                c.summary_one_liner or "",
                "Yes" if c.linkedin else "No",
                "Yes" if c.github else "No",
                c.created_at.isoformat() if c.created_at else "",
                c.updated_at.isoformat() if hasattr(c, 'updated_at') and c.updated_at else "",
            ])

        csv_content = output.getvalue()
        output.close()
        
        logger.info("CSV export complete", extra={
            "user_id": request.user.id,
            "csv_size_bytes": len(csv_content),
        })

        resp = HttpResponse(csv_content, content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="candidates_export.csv"'
        return resp
