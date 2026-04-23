import re
from django.db import transaction
from typing import Any, Dict, List, Optional

from candidates.models import Candidate, Skill, EducationEntry, ExperienceEntry
from .models import ResumeDocument, ParseRun

# Model limits (candidates.Skill.name max_length=100, etc.)
_SKILL_NAME_MAX = 100
_STR255 = 255
_DATEISH = re.compile(r"\d{4}")


def _coerce_skill_item(s: Any) -> Optional[Dict[str, Any]]:
    """
    LLM output sometimes uses skills: ["Python", ...] instead of schema objects.
    Normalize to a dict so we can persist to Skill.
    """
    if isinstance(s, str):
        name = s.strip()[:_SKILL_NAME_MAX]
        if not name:
            return None
        return {
            "name": name,
            "category": None,
            "confidence": 0.0,
            "evidence": [],
        }
    if isinstance(s, dict):
        return s
    return None


def _coerce_education_item(ed: Any) -> Optional[Dict[str, Any]]:
    """LLM may return education as a list of degree strings instead of objects."""
    if isinstance(ed, str):
        t = ed.strip()[:_STR255]
        if not t:
            return None
        return {
            "institution": None,
            "degree": t,
            "field_of_study": None,
            "start_date": None,
            "end_date": None,
            "grade": None,
            "confidence": 0.0,
            "evidence": [],
        }
    if isinstance(ed, dict):
        return ed
    return None


def _coerce_experience_list(raw: Any) -> List[Dict[str, Any]]:
    """
    LLM may return experience as free-form lines (title | company, then a date line).
    Convert to object-shaped dicts for ExperienceEntry.
    """
    if not raw or not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    i, n = 0, len(raw)
    while i < n:
        ex = raw[i]
        if isinstance(ex, dict):
            out.append(ex)
            i += 1
            continue
        if not isinstance(ex, str):
            i += 1
            continue
        line = ex.strip()
        if not line:
            i += 1
            continue
        d: Dict[str, Any] = {
            "company": None,
            "title": None,
            "employment_type": None,
            "start_date": None,
            "end_date": None,
            "is_current": False,
            "location": None,
            "bullets": [],
            "technologies": [],
            "confidence": 0.0,
            "evidence": [],
        }
        if "|" in line:
            a, b = [x.strip() for x in line.split("|", 1)]
            d["title"] = a[:_STR255] if a else None
            d["company"] = b[:_STR255] if b else None
        else:
            d["title"] = line[:_STR255]
        nxt = raw[i + 1] if i + 1 < n else None
        if (
            isinstance(nxt, str)
            and nxt.strip()
            and _DATEISH.search(nxt)
            and "|" not in nxt
        ):
            d["bullets"] = [nxt.strip()]
            i += 2
        else:
            i += 1
        out.append(d)
    return out


def _coerce_project_item(p: Any) -> Optional[Dict[str, Any]]:
    if isinstance(p, str):
        n = p.strip()[:_STR255]
        if not n:
            return None
        return {
            "name": n,
            "description": None,
            "url": None,
            "technologies": [],
            "start_date": None,
            "end_date": None,
            "confidence": 0.0,
            "evidence": [],
        }
    if isinstance(p, dict):
        return p
    return None


def _coerce_certification_item(c: Any) -> Optional[Dict[str, Any]]:
    if isinstance(c, str):
        n = c.strip()[:_STR255]
        if not n:
            return None
        return {
            "name": n,
            "issuer": None,
            "date_issued": None,
            "date_expires": None,
            "credential_id": None,
            "url": None,
            "confidence": 0.0,
            "evidence": [],
        }
    if isinstance(c, dict):
        return c
    return None


def normalize_llm_array_shapes_for_schema(llm_json: Dict[str, Any]) -> None:
    """
    LLMs often return skills/education/... as string arrays. The jsonschema expects
    objects. Coerce in place before validation so the Warnings tab is not filled with
    '... is not of type object' noise; persistence already accepts these shapes.
    """
    if not isinstance(llm_json, dict):
        return

    sks = llm_json.get("skills")
    if isinstance(sks, list):
        out = []
        for s in sks:
            c = _coerce_skill_item(s)
            if c is not None:
                out.append(c)
        llm_json["skills"] = out

    eds = llm_json.get("education")
    if isinstance(eds, list):
        out = []
        for ed in eds:
            c = _coerce_education_item(ed)
            if c is not None:
                out.append(c)
        llm_json["education"] = out

    exs = llm_json.get("experience")
    if isinstance(exs, list) and any(isinstance(x, str) for x in exs):
        llm_json["experience"] = _coerce_experience_list(exs)

    prs = llm_json.get("projects")
    if isinstance(prs, list):
        out = []
        for p in prs:
            c = _coerce_project_item(p)
            if c is not None:
                out.append(c)
        llm_json["projects"] = out

    certs = llm_json.get("certifications")
    if isinstance(certs, list):
        out = []
        for c in certs:
            x = _coerce_certification_item(c)
            if x is not None:
                out.append(x)
        llm_json["certifications"] = out


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
        s = _coerce_skill_item(s)
        if not s:
            continue
        name = (s.get("name") or "").strip()[:_SKILL_NAME_MAX]
        if not name:
            continue
        Skill.objects.create(
            candidate=candidate,
            name=name,
            category=s.get("category"),
            confidence=float(s.get("confidence") or 0.0),
            evidence=s.get("evidence") or [],
        )

    for ed in normalized.get("education", []) or []:
        ed = _coerce_education_item(ed)
        if not ed:
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

    for ex in _coerce_experience_list(normalized.get("experience")):
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

