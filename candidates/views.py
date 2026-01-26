import csv
from io import StringIO

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.throttling import ScopedRateThrottle

from core.responses import ok, fail
from .models import Candidate, CandidateEditLog
from .serializers import (
    CandidateListSerializer,
    CandidateDetailSerializer,
    CandidatePatchSerializer,
    CandidateEditLogSerializer,
)


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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "headline", "location", "primary_role"]
    ordering_fields = ["created_at", "overall_confidence", "full_name"]

    # Default throttle applies; we also apply scoped throttles on specific actions.
    throttle_classes = [ScopedRateThrottle]

    def get_queryset(self):
        # Ownership filter: only candidates from resumes uploaded by this user
        qs = Candidate.objects.filter(resume_document__uploaded_by=self.request.user).order_by("-created_at")

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

        # Return full detail payload
        return ok(CandidateDetailSerializer(candidate).data, status=200)

    @action(detail=True, methods=["get"], url_path="edit-logs")
    def edit_logs(self, request, pk=None):
        candidate = self.get_object()
        logs = candidate.edit_logs.order_by("-edited_at")
        return ok(CandidateEditLogSerializer(logs, many=True).data, status=200)

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """
        CSV export of current filtered candidate list.
        Respects the same filters as list: q, skill, role, min_conf.
        """
        qs = self.filter_queryset(self.get_queryset())

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
            "primary_role",
            "seniority",
            "overall_confidence",
            "created_at",
        ])

        for c in qs:
            writer.writerow([
                c.id,
                c.full_name or "",
                c.headline or "",
                c.location or "",
                c.primary_email or "",
                c.primary_phone or "",
                c.primary_role or "",
                c.seniority or "",
                c.overall_confidence,
                c.created_at.isoformat() if c.created_at else "",
            ])

        csv_content = output.getvalue()
        output.close()

        resp = HttpResponse(csv_content, content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="candidates_export.csv"'
        return resp
