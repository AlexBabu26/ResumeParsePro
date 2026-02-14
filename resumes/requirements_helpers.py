from django.utils import timezone
from .pipeline import call_requirements_validation

def _candidate_meets_requirements(candidate, requirements: dict, use_llm: bool = True) -> tuple[bool, list[str]]:
    """
    Check if a candidate meets the specified requirements.
    Returns (meets_requirements, reasons_for_rejection).
    
    This function delegates to either LLM-based validation (slower, more accurate)
    or string-based validation (faster, less accurate).
    """
    if not requirements:
        return True, []
    
    # Check if LLM validation is requested (default yes)
    use_llm_req = requirements.get("use_llm_validation", True)
    
    if use_llm and use_llm_req:
        return _candidate_meets_requirements_llm(candidate, requirements)
    else:
        return _candidate_meets_requirements_string(candidate, requirements)


def _candidate_meets_requirements_llm(candidate, requirements: dict) -> tuple[bool, list[str]]:
    """
    Use LLM to validate requirements (semantic matching).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Serialize candidate to dict for LLM
    candidate_data = {
        "full_name": candidate.full_name,
        "primary_role": candidate.primary_role,
        "seniority": candidate.seniority,
        # "location": candidate.location,  # Was missing in my draft, adding it
        "location": candidate.location,
        "overall_confidence": candidate.overall_confidence,
        "skills": [s.name for s in candidate.skills.all()],
        "experience": [
            {
                "company": e.company,
                "title": e.title,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "is_current": e.is_current,
                "description": e.title  # Simplified for LLM prompt context
            } for e in candidate.experience.all()
        ],
        "education": [
            {
                "institution": e.institution,
                "degree": e.degree,
            } for e in candidate.education.all()
        ]
    }
    
    try:
        result = call_requirements_validation(candidate_data, requirements)
        # Parse result
        # expected: {"parsed_json": {"meets_requirements": bool, "reasons": []}}
        parsed = result.get("parsed_json", {})
        if not parsed:
            # Fallback to string check if LLM fails
            logger.warning("LLM requirements validation returned empty/invalid JSON, falling back to string check")
            return _candidate_meets_requirements_string(candidate, requirements)
            
        meets = parsed.get("meets_requirements", False)
        reasons = parsed.get("reasons", [])
        if isinstance(reasons, str): reasons = [reasons]
        
        if not meets and not reasons:
            reasons = ["LLM declined candidate without providing specific reasons."]
            
        return meets, reasons
        
    except Exception as e:
        logger.error(f"LLM requirements validation failed: {str(e)}")
        # Fallback
        return _candidate_meets_requirements_string(candidate, requirements)


def _candidate_meets_requirements_string(candidate, requirements: dict) -> tuple[bool, list[str]]:
    """
    Basic string matching for requirements (faster, cheaper, but less accurate).
    """
    from django.utils.dateparse import parse_date
    
    reasons = []
    
    # Helper to clean strings
    def clean(s): return str(s).lower().strip() if s else ""
    
    # 1. Required Skills (ALL must be present)
    req_skills = requirements.get("required_skills", [])
    if req_skills:
        cand_skills = {clean(s.name) for s in candidate.skills.all()}
        missing = []
        for req in req_skills:
            # Check for partial match too? No, exact match for required skills usually.
            # But let's allow substring match for leniency
            req_clean = clean(req)
            found = False
            if req_clean in cand_skills:
                found = True
            else:
                for cs in cand_skills:
                    if req_clean in cs or cs in req_clean:
                        found = True
                        break
            if not found:
                missing.append(req)
        
        if missing:
             reasons.append(f"Missing required skills: {', '.join(missing)}")

    # 2. Any Skills (AT LEAST ONE must be present)
    any_skills = requirements.get("any_skills", [])
    if any_skills:
        cand_skills = {clean(s.name) for s in candidate.skills.all()}
        found = False
        for req in any_skills:
            req_clean = clean(req)
            if req_clean in cand_skills:
                found = True
                break
            # Try substrings
            for cs in cand_skills:
                if req_clean in cs or cs in req_clean:
                    found = True
                    break
            if found: break
            
        if not found:
            reasons.append(f"Missing any of the preferred skills: {', '.join(any_skills)}")

    # 3. Minimum Experience
    min_exp = requirements.get("min_years_experience")
    if min_exp is not None:
        try:
            total_years = 0.0
            for exp in candidate.experience.all():
                start = parse_date(exp.start_date) if exp.start_date else None
                end = parse_date(exp.end_date) if exp.end_date else None
                
                if start:
                    if not end and exp.is_current:
                        end = timezone.now().date()
                    
                    if end and end > start:
                        delta = (end - start).days / 365.25
                        if delta > 0:
                            total_years += delta
            
            if total_years < float(min_exp):
                reasons.append(f"Insufficient experience: {total_years:.1f} years (minimum {min_exp})")
        except Exception:
            # Date parsing failed? Ignore experience check or fail?
            # Let's ignore it to be safe, or assume 0.
            pass

    # 4. Education Degree
    req_degrees = requirements.get("required_education_degree", [])
    if req_degrees:
        cand_degrees = [clean(e.degree) for e in candidate.education.all()]
        has_degree = False
        for req in req_degrees:
            req_clean = clean(req)
            for deg in cand_degrees: # e.g. "bachelor of science"
                if req_clean in deg: # "bachelor" in "bachelor of science"
                    has_degree = True
                    break
            if has_degree: break
        
        if not has_degree:
             reasons.append(f"Missing required degree: {', '.join(req_degrees)}")

    # 5. Primary Role
    req_roles = requirements.get("required_primary_role", [])
    if req_roles:
        cand_role = clean(candidate.primary_role)
        match = False
        for role in req_roles:
            role_clean = clean(role)
            if role_clean in cand_role or cand_role in role_clean:
                match = True
                break
        if not match:
            reasons.append(f"Role mismatch: {candidate.primary_role} (required: {', '.join(req_roles)})")

    # 6. Seniority
    req_seniority = requirements.get("required_seniority", [])
    if req_seniority:
        cand_seniority = clean(candidate.seniority)
        match = False
        for sens in req_seniority:
             if clean(sens) == cand_seniority: 
                 match = True
                 break
        if not match:
             reasons.append(f"Seniority mismatch: {candidate.seniority} (required: {', '.join(req_seniority)})")
             
    # 7. Location
    loc_req = requirements.get("location_contains")
    if loc_req:
        cand_loc = clean(candidate.location)
        if clean(loc_req) not in cand_loc:
             reasons.append(f"Location mismatch: {candidate.location} (must contain '{loc_req}')")

    # 8. Confidence
    min_conf = requirements.get("min_confidence")
    if min_conf is not None:
        if candidate.overall_confidence < float(min_conf):
             reasons.append(f"Low confidence score: {candidate.overall_confidence:.2f} (minimum {min_conf})")

    return (len(reasons) == 0), reasons
