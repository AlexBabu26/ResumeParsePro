from django.db import transaction
from typing import Any, Dict

from candidates.models import Candidate, Skill, EducationEntry, ExperienceEntry
from .models import ResumeDocument, ParseRun


@transaction.atomic
def persist_candidate_from_normalized(doc: ResumeDocument, run: ParseRun, normalized: Dict[str, Any]) -> int:
    cand = normalized.get("candidate") or {}
    links = cand.get("links") or {}
    cls = normalized.get("classification") or {}
    summ = normalized.get("summary") or {}
    quality = normalized.get("quality") or {}

    primary_email = (cand.get("emails") or [None])[0]
    primary_phone = (cand.get("phones") or [None])[0]

    candidate = Candidate.objects.create(
        resume_document=doc,
        parse_run=run,
        full_name=cand.get("full_name"),
        location=cand.get("location"),
        headline=cand.get("headline"),
        primary_email=primary_email,
        primary_phone=primary_phone,
        linkedin=links.get("linkedin"),
        github=links.get("github"),
        portfolio=links.get("portfolio"),
        primary_role=cls.get("primary_role"),
        seniority=cls.get("seniority"),
        overall_confidence=float(quality.get("overall_confidence") or 0.0),
        summary_one_liner=summ.get("one_liner"),
        summary_highlights=summ.get("highlights") or [],
    )

    for s in normalized.get("skills", []) or []:
        if not isinstance(s, dict):
            continue
        Skill.objects.create(
            candidate=candidate,
            name=s.get("name"),
            category=s.get("category"),
            confidence=float(s.get("confidence") or 0.0),
            evidence=s.get("evidence") or [],
        )

    for ed in normalized.get("education", []) or []:
        if not isinstance(ed, dict):
            continue
        EducationEntry.objects.create(
            candidate=candidate,
            institution=ed.get("institution"),
            degree=ed.get("degree"),
            field_of_study=ed.get("field_of_study"),
            start_date=ed.get("start_date"),
            end_date=ed.get("end_date"),
            grade=ed.get("grade"),
            confidence=float(ed.get("confidence") or 0.0),
            evidence=ed.get("evidence") or [],
        )

    for ex in normalized.get("experience", []) or []:
        if not isinstance(ex, dict):
            continue
        ExperienceEntry.objects.create(
            candidate=candidate,
            company=ex.get("company"),
            title=ex.get("title"),
            employment_type=ex.get("employment_type"),
            start_date=ex.get("start_date"),
            end_date=ex.get("end_date"),
            is_current=bool(ex.get("is_current", False)),
            location=ex.get("location"),
            bullets=ex.get("bullets") or [],
            technologies=ex.get("technologies") or [],
            confidence=float(ex.get("confidence") or 0.0),
            evidence=ex.get("evidence") or [],
        )

    return candidate.id

