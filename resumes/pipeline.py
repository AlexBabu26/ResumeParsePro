import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

import requests
from django.conf import settings
from jsonschema import Draft202012Validator
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .schema import RESUME_JSON_SCHEMA
from .utils import parse_json_safely

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
URL_RE = re.compile(r"(https?://[^\s)>\]]+)")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d \-().]{7,}\d)(?!\d)")

# Model pricing per 1M tokens (USD)
MODEL_PRICING = {
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
    "anthropic/claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "anthropic/claude-3-opus": {"input": 15.00, "output": 75.00},
    "google/gemini-pro": {"input": 0.125, "output": 0.375},
    "meta-llama/llama-3-8b-instruct": {"input": 0.05, "output": 0.05},
    "xiaomi/mimo-v2-flash:free": {"input": 0.0, "output": 0.0},
}

CANONICAL_TEMPLATE = {
    "schema_version": "1.0",
    "candidate": {
        "full_name": None,
        "headline": None,
        "location": None,
        "emails": [],
        "phones": [],
        "links": {"linkedin": None, "github": None, "portfolio": None, "other": []},
    },
    "skills": [],
    "education": [],
    "experience": [],
    "projects": [],
    "certifications": [],
    "classification": {"primary_role": None, "secondary_roles": [], "seniority": None, "confidence": 0.0, "rationale": None},
    "summary": {"one_liner": None, "highlights": []},
    "quality": {"warnings": [], "missing_critical_fields": [], "overall_confidence": 0.0},
}

EXTRACTION_SYSTEM_PROMPT = """You are a resume information extraction engine.

Rules you MUST follow:
1) Output ONLY valid JSON. No markdown. No commentary.
2) Extract facts ONLY from the provided resume text. Do not infer or invent.
3) If a field is unknown or not present, use null (for scalars) or [] (for arrays).
4) Every evidence string you provide MUST be an exact substring copied from the resume text.
5) Do not include any keys that are not in the provided schema/template.
6) Confidence values must be between 0 and 1.
7) Do not fabricate emails, phone numbers, links, institutions, companies, titles, or dates.
8) For dates, use YYYY-MM-DD format when possible, or YYYY-MM, or just YYYY if only year is known.
9) For current positions, set end_date to null and is_current to true.

Return JSON that conforms exactly to the provided schema/template.
"""

CLASSIFY_SYSTEM_PROMPT = """You are a classifier for candidate job role and seniority based ONLY on provided structured resume data.
Output ONLY valid JSON. No markdown. No commentary. Do not invent facts. Confidence must be 0..1.

## Role Categories (choose the most appropriate):
- Software Engineer / Developer
- Data Scientist / ML Engineer
- Data Analyst / Business Intelligence
- DevOps / SRE / Platform Engineer
- Product Manager
- Engineering Manager / Tech Lead
- Designer (UX/UI)
- QA / Test Engineer
- Security Engineer
- Solutions Architect
- Technical Writer
- Other (specify)

## Seniority Levels (from experience and titles):
- Intern: Student or recent graduate with < 1 year experience
- Junior: 0-2 years experience, learning the craft
- Mid: 2-5 years experience, independent contributor
- Senior: 5-8 years experience, mentors others, leads projects
- Staff: 8-12 years experience, technical leadership across teams
- Principal: 12+ years experience, organization-wide technical impact
- Lead/Manager: People management responsibilities

## Classification Guidelines:
- Base role on most recent and dominant experience
- Consider job titles, responsibilities, and technologies used
- Seniority should reflect actual experience level, not just titles
- If unclear, use lower confidence score
"""

SUMMARY_SYSTEM_PROMPT = """You generate concise recruiter summaries from structured resume data.
Output ONLY valid JSON. No markdown. No commentary. Do not invent facts.

## Guidelines:
- one_liner: A single compelling sentence (max 150 chars) highlighting the candidate's strongest value proposition
- highlights: Up to 5 bullet points (each max 100 chars) covering:
  * Key technical skills or domain expertise
  * Notable achievements or impact (quantified if possible)
  * Relevant experience at well-known companies
  * Educational credentials if notable
  * Unique differentiators

## Tone:
- Professional and action-oriented
- Focus on facts, not fluff
- Use active voice
- Emphasize measurable achievements when available
"""

_validator = Draft202012Validator(RESUME_JSON_SCHEMA)


def _ensure_list(x) -> List:
    return x if isinstance(x, list) else []


def _clamp01(v: Any) -> float:
    try:
        v = float(v)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, v))


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate API cost in USD for a given model and token usage."""
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    input_tokens = input_tokens or 0
    output_tokens = output_tokens or 0
    cost = (input_tokens * pricing["input"] / 1_000_000) + (output_tokens * pricing["output"] / 1_000_000)
    return round(cost, 6)


def get_model_timeout(model: str) -> int:
    """Get timeout for a specific model from settings."""
    timeouts = getattr(settings, "OPENROUTER_MODEL_TIMEOUTS", {})
    default = getattr(settings, "OPENROUTER_DEFAULT_TIMEOUT", 90)
    return timeouts.get(model, default)


def extract_known_pii(text: str) -> Dict[str, List[str]]:
    """Extract emails, phones, and URLs from text using regex."""
    emails = sorted(set(EMAIL_RE.findall(text)))
    urls = sorted(set(URL_RE.findall(text)))
    phones = sorted(set(m.strip() for m in PHONE_RE.findall(text)))
    phones = [p for p in phones if sum(c.isdigit() for c in p) >= 10]
    
    logger.debug("PII extraction complete", extra={
        "emails_count": len(emails),
        "phones_count": len(phones),
        "urls_count": len(urls),
    })
    return {"emails_found": emails, "phones_found": phones, "links_found": urls}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def openrouter_call(model: str, system_prompt: str, user_prompt: str, temperature: float, timeout_s: int = None) -> Dict[str, Any]:
    """
    Call OpenRouter API with retry logic and cost tracking.
    
    Features:
    - Automatic retry with exponential backoff for transient errors
    - Model-specific timeouts
    - Cost calculation
    - Structured logging
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        logger.error("OPENROUTER_API_KEY not configured")
        raise RuntimeError("OPENROUTER_API_KEY not set")

    # Use model-specific timeout if not provided
    if timeout_s is None:
        timeout_s = get_model_timeout(model)

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "temperature": float(temperature),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    logger.info("OpenRouter API call starting", extra={
        "model": model,
        "temperature": temperature,
        "timeout_s": timeout_s,
        "prompt_length": len(user_prompt),
    })

    t0 = time.time()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    except requests.Timeout:
        logger.error("OpenRouter API timeout", extra={
            "model": model,
            "timeout_s": timeout_s,
        })
        raise
    except requests.ConnectionError as e:
        logger.error("OpenRouter API connection error", extra={
            "model": model,
            "error": str(e),
        })
        raise
    
    latency_ms = int((time.time() - t0) * 1000)

    if resp.status_code == 429:
        logger.warning("OpenRouter rate limited", extra={
            "model": model,
            "status_code": resp.status_code,
        })
        raise requests.ConnectionError("Rate limited (429)")
    
    if resp.status_code >= 500:
        logger.warning("OpenRouter server error", extra={
            "model": model,
            "status_code": resp.status_code,
        })
        raise requests.ConnectionError(f"Server error ({resp.status_code})")

    if resp.status_code != 200:
        logger.error("OpenRouter API error", extra={
            "model": model,
            "status_code": resp.status_code,
            "response": resp.text[:500],
        })
        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    
    input_tokens = usage.get("prompt_tokens")
    output_tokens = usage.get("completion_tokens")
    cost = calculate_cost(model, input_tokens, output_tokens)

    logger.info("OpenRouter API call complete", extra={
        "model": model,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    })

    return {
        "content": content,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }


def call_extract(resume_text: str, known_pii: Dict[str, List[str]]) -> Dict[str, Any]:
    model = getattr(settings, "OPENROUTER_EXTRACT_MODEL", "openai/gpt-4o-mini")
    temperature = float(getattr(settings, "OPENROUTER_TEMPERATURE", 0.1))

    user_prompt = (
        "Extract structured resume data from the text below.\n\n"
        "Schema/template (must match exactly):\n"
        f"{json.dumps(CANONICAL_TEMPLATE, ensure_ascii=False)}\n\n"
        "Known verified contact hints (prefer these; do not contradict them):\n"
        f"{json.dumps(known_pii, ensure_ascii=False)}\n\n"
        "Resume text:\n<<<\n"
        f"{resume_text}\n"
        ">>>"
    )

    r = openrouter_call(model, EXTRACTION_SYSTEM_PROMPT, user_prompt, temperature, timeout_s=90)
    parsed = parse_json_safely(r["content"])
    return {"parsed_json": parsed, "model": model, **r}


def validate_against_schema(llm_json: Dict[str, Any]) -> List[str]:
    errors = []
    if not isinstance(llm_json, dict):
        return ["LLM output is not a JSON object"]
    for e in _validator.iter_errors(llm_json):
        path = ".".join([str(p) for p in e.path]) if e.path else "(root)"
        errors.append(f"{path}: {e.message}")
        if len(errors) >= 20:
            errors.append("... (truncated)")
            break
    return errors


def normalize_and_validate(llm_json: Dict[str, Any], raw_text: str, known_pii: Dict[str, List[str]]) -> Tuple[Dict[str, Any], List[str], List[str], str]:
    warnings: List[str] = []
    missing: List[str] = []

    schema_errors = validate_against_schema(llm_json)
    if schema_errors:
        warnings.append("jsonschema_validation_failed")
        warnings.extend(schema_errors)

    # Start from canonical template (ensures keys exist)
    norm = json.loads(json.dumps(CANONICAL_TEMPLATE))
    if isinstance(llm_json, dict):
        for k in norm.keys():
            if k in llm_json:
                norm[k] = llm_json[k]

    # anti-hallucination for emails/phones using regex findings
    cand = norm.get("candidate") or {}
    found_emails = set(known_pii["emails_found"])
    found_phones = set(known_pii["phones_found"])

    emails = _ensure_list(cand.get("emails"))
    phones = _ensure_list(cand.get("phones"))

    if found_emails:
        emails = [e for e in emails if e in found_emails] or list(found_emails)
    else:
        emails = [e for e in emails if EMAIL_RE.fullmatch(e or "")]

    if found_phones:
        phones = [p for p in phones if p in found_phones] or list(found_phones)
    else:
        phones = [p for p in phones if sum(c.isdigit() for c in (p or "")) >= 10]

    links = cand.get("links") if isinstance(cand.get("links"), dict) else {}
    urls = known_pii["links_found"]
    linkedin = next((u for u in urls if "linkedin.com" in u.lower()), None)
    github = next((u for u in urls if "github.com" in u.lower()), None)
    portfolio = next((u for u in urls if u not in {linkedin, github}), None)

    # drop hallucinated links not in extracted URLs
    def keep_if_found(v):
        return v if (not urls or v in urls) else None

    norm["candidate"] = {
        "full_name": cand.get("full_name"),
        "headline": cand.get("headline"),
        "location": cand.get("location"),
        "emails": emails,
        "phones": phones,
        "links": {
            "linkedin": keep_if_found(links.get("linkedin") or linkedin),
            "github": keep_if_found(links.get("github") or github),
            "portfolio": keep_if_found(links.get("portfolio") or portfolio),
            "other": [u for u in _ensure_list(links.get("other")) if (not urls or u in urls)],
        },
    }

    # simple confidence heuristic
    score = 0.2
    if emails or phones:
        score += 0.2
    if len(norm.get("skills", [])) >= 5:
        score += 0.2
    if any(e.get("company") and e.get("title") for e in _ensure_list(norm.get("experience")) if isinstance(e, dict)):
        score += 0.2
    if any(ed.get("institution") and ed.get("degree") for ed in _ensure_list(norm.get("education")) if isinstance(ed, dict)):
        score += 0.2
    score = _clamp01(score)

    if not norm["candidate"].get("full_name"):
        missing.append("candidate.full_name")
    if not norm["candidate"].get("emails") and not norm["candidate"].get("phones"):
        missing.append("candidate.emails/phones")

    norm["quality"]["warnings"] = warnings
    norm["quality"]["missing_critical_fields"] = missing
    norm["quality"]["overall_confidence"] = score

    if (not norm.get("skills")) and (not norm.get("education")) and (not norm.get("experience")) and missing:
        return norm, warnings, missing, "failed"

    # Determine status:
    # - if schema errors exist, we treat as partial unless we still have good extraction
    if schema_errors and (len(missing) >= 1):
        return norm, warnings, missing, "partial"

    return norm, warnings, missing, ("partial" if len(missing) >= 2 else "success")


def call_classify(normalized_json: Dict[str, Any]) -> Dict[str, Any]:
    """Classify candidate role and seniority using LLM."""
    model = getattr(settings, "OPENROUTER_CLASSIFY_MODEL", "openai/gpt-4o-mini")
    temperature = float(getattr(settings, "OPENROUTER_CLASSIFY_TEMPERATURE", 0.1))

    user_prompt = (
        "Classify the candidate based on the resume data.\n\n"
        "Return ONLY JSON with keys:\n"
        "- primary_role: The main job role/title that best fits this candidate\n"
        "- secondary_roles: Array of up to 3 alternative roles they could fill\n"
        "- seniority: One of [Intern, Junior, Mid, Senior, Staff, Principal, Lead/Manager]\n"
        "- confidence: Float 0-1 indicating classification confidence\n"
        "- rationale: Brief explanation of the classification\n\n"
        f"Structured resume JSON:\n{json.dumps(normalized_json, ensure_ascii=False)}"
    )

    logger.debug("Calling classify LLM", extra={"model": model})
    r = openrouter_call(model, CLASSIFY_SYSTEM_PROMPT, user_prompt, temperature)
    parsed = parse_json_safely(r["content"])
    logger.info("Classification complete", extra={
        "model": model,
        "latency_ms": r["latency_ms"],
        "primary_role": parsed.get("primary_role") if isinstance(parsed, dict) else None,
    })
    return {"parsed_json": parsed, "model": model, **r}


def call_summary(normalized_json: Dict[str, Any]) -> Dict[str, Any]:
    """Generate recruiter-friendly summary using LLM."""
    model = getattr(settings, "OPENROUTER_SUMMARY_MODEL", "openai/gpt-4o-mini")
    temperature = float(getattr(settings, "OPENROUTER_SUMMARY_TEMPERATURE", 0.2))

    user_prompt = (
        "Create a recruiter-friendly summary of this candidate.\n\n"
        "Return ONLY JSON with keys:\n"
        "- one_liner: A single compelling sentence (max 150 chars) summarizing the candidate\n"
        "- highlights: Array of up to 5 bullet points (each max 100 chars) with key strengths\n\n"
        f"Structured resume JSON:\n{json.dumps(normalized_json, ensure_ascii=False)}"
    )

    logger.debug("Calling summary LLM", extra={"model": model})
    r = openrouter_call(model, SUMMARY_SYSTEM_PROMPT, user_prompt, temperature)
    parsed = parse_json_safely(r["content"])
    logger.info("Summary complete", extra={
        "model": model,
        "latency_ms": r["latency_ms"],
    })
    return {"parsed_json": parsed, "model": model, **r}


REQUIREMENTS_VALIDATION_SYSTEM_PROMPT = """You are a candidate requirements validator. 
Evaluate if a candidate meets the specified job requirements based ONLY on the provided candidate data.
Output ONLY valid JSON. No markdown. No commentary.

Be strict but fair:
- For role matching, consider semantic similarity (e.g., "Software Developer" matches "Software Engineer")
- For skills, check if the candidate has equivalent or related skills
- Be honest about mismatches - don't approve candidates who clearly don't fit
"""


def call_requirements_validation(candidate_data: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use LLM to validate if candidate meets requirements.
    Returns: {"meets_requirements": bool, "reasons": [], "confidence": float}
    """
    model = getattr(settings, "OPENROUTER_CLASSIFY_MODEL", "openai/gpt-4o-mini")
    temperature = 0.1  # Low temperature for consistent results
    
    user_prompt = (
        "Evaluate if this candidate meets the job requirements.\n\n"
        "Return ONLY JSON with these keys:\n"
        "- meets_requirements: boolean (true if candidate meets ALL requirements)\n"
        "- reasons: array of strings explaining each requirement check result\n"
        "- confidence: float 0-1 (how confident you are in the assessment)\n\n"
        f"CANDIDATE DATA:\n{json.dumps(candidate_data, ensure_ascii=False, indent=2)}\n\n"
        f"REQUIREMENTS:\n{json.dumps(requirements, ensure_ascii=False, indent=2)}\n\n"
        "Evaluate each requirement strictly:\n"
        "- required_primary_role: Does the candidate's role/experience match semantically?\n"
        "- required_skills: Does the candidate have ALL these skills (or equivalent)?\n"
        "- any_skills: Does the candidate have AT LEAST ONE of these skills?\n"
        "- min_years_experience: Does total experience meet the minimum?\n"
        "- required_education_degree: Does the candidate have this level of education?\n"
        "- required_seniority: Does the candidate's seniority level match?\n"
        "- location_contains: Is the candidate in or near the required location?\n"
        "- min_confidence: Is the parsing confidence score high enough?\n"
    )
    
    r = openrouter_call(model, REQUIREMENTS_VALIDATION_SYSTEM_PROMPT, user_prompt, temperature, timeout_s=60)
    parsed = parse_json_safely(r["content"])
    
    if not isinstance(parsed, dict):
        return {"meets_requirements": False, "reasons": ["LLM validation failed"], "confidence": 0.0}
    
    return {
        "meets_requirements": bool(parsed.get("meets_requirements", False)),
        "reasons": parsed.get("reasons", []),
        "confidence": _clamp01(parsed.get("confidence", 0.0)),
        "model": model,
        "latency_ms": r["latency_ms"],
    }


def enrich_with_classification_and_summary(normalized: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Enrich normalized resume data with classification and summary.
    
    Runs classification and summary LLM calls in parallel to reduce latency.
    """
    warnings = _ensure_list(normalized.get("quality", {}).get("warnings"))
    warnings = [w for w in warnings if isinstance(w, str)]
    
    total_cost = 0.0
    cls_result = None
    sm_result = None
    
    logger.info("Starting parallel classification and summary")
    
    # Run classification and summary in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        cls_future = executor.submit(call_classify, normalized)
        sm_future = executor.submit(call_summary, normalized)
        
        # Collect results
        for future in as_completed([cls_future, sm_future]):
            try:
                if future == cls_future:
                    cls_result = future.result()
                else:
                    sm_result = future.result()
            except Exception as e:
                if future == cls_future:
                    warnings.append(f"classification_failed: {str(e)}")
                    logger.warning("Classification failed", extra={"error": str(e)})
                else:
                    warnings.append(f"summary_failed: {str(e)}")
                    logger.warning("Summary failed", extra={"error": str(e)})

    # Process classification result
    if cls_result:
        obj = cls_result["parsed_json"] if isinstance(cls_result["parsed_json"], dict) else {}
        normalized["classification"] = {
            "primary_role": obj.get("primary_role"),
            "secondary_roles": [s for s in _ensure_list(obj.get("secondary_roles")) if isinstance(s, str)][:3],
            "seniority": obj.get("seniority"),
            "confidence": _clamp01(obj.get("confidence")),
            "rationale": obj.get("rationale"),
        }
        cost = cls_result.get("cost_usd", 0.0)
        total_cost += cost
        warnings.append(f"classification_model={cls_result['model']}, latency_ms={cls_result['latency_ms']}, cost_usd={cost}")

    # Process summary result
    if sm_result:
        obj = sm_result["parsed_json"] if isinstance(sm_result["parsed_json"], dict) else {}
        normalized["summary"] = {
            "one_liner": obj.get("one_liner"),
            "highlights": [h for h in _ensure_list(obj.get("highlights")) if isinstance(h, str)][:5],
        }
        cost = sm_result.get("cost_usd", 0.0)
        total_cost += cost
        warnings.append(f"summary_model={sm_result['model']}, latency_ms={sm_result['latency_ms']}, cost_usd={cost}")

    normalized.setdefault("quality", {})
    normalized["quality"]["warnings"] = warnings
    normalized["quality"]["enrichment_cost_usd"] = total_cost
    
    logger.info("Enrichment complete", extra={
        "total_cost_usd": total_cost,
        "classification_success": cls_result is not None,
        "summary_success": sm_result is not None,
    })
    
    return normalized, warnings

