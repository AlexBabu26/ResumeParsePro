import hashlib
import logging
import re
import unicodedata
from datetime import datetime

from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from core.responses import ok, fail

from .models import ResumeDocument, ParseRun
from .serializers import ResumeDocumentSerializer, ResumeUploadSerializer, BulkResumeUploadSerializer, ParseRunSerializer
from .tasks import parse_resume_parse_run
from .requirements_helpers import _candidate_meets_requirements

from candidates.models import Candidate

logger = logging.getLogger(__name__)


# Extraction logic moved to resumes.extraction.py


def sha256_of_uploaded_file(uploaded_file) -> str:
    h = hashlib.sha256()
    pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else None
    for chunk in uploaded_file.chunks():
        h.update(chunk)
    # reset pointer so Django can save it
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(pos or 0)
    return h.hexdigest()


def _calculate_years_experience(candidate: Candidate) -> float:
    """Calculate total years of experience from experience entries"""
    from datetime import datetime
    
    try:
        from dateutil import parser
        use_dateutil = True
    except ImportError:
        use_dateutil = False
    
    total_years = 0.0
    for exp in candidate.experience.all():
        if not exp.start_date:
            continue
        
        try:
            if use_dateutil:
                start = parser.parse(exp.start_date, default=datetime(2000, 1, 1))
                end = parser.parse(exp.end_date, default=datetime.now()) if exp.end_date else datetime.now()
            else:
                # Fallback: simple date parsing (YYYY-MM-DD format)
                start_str = str(exp.start_date)[:10]  # Take first 10 chars (YYYY-MM-DD)
                end_str = str(exp.end_date)[:10] if exp.end_date else None
                
                try:
                    start = datetime.strptime(start_str, "%Y-%m-%d")
                    end = datetime.strptime(end_str, "%Y-%m-%d") if end_str else datetime.now()
                except ValueError:
                    # If parsing fails, skip this entry
                    continue
            
            # Calculate years
            delta = end - start
            years = delta.days / 365.25
            total_years += max(0, years)
        except (ValueError, TypeError):
            # If date parsing fails, skip this entry
            continue
    
    return total_years


def _build_candidate_data_for_validation(candidate: Candidate) -> dict:
    """Build a dictionary of candidate data for LLM validation."""
    return {
        "full_name": candidate.full_name,
        "primary_role": candidate.primary_role,
        "seniority": candidate.seniority,
        "location": candidate.location,
        "headline": candidate.headline,
        "skills": [{"name": s.name, "category": s.category} for s in candidate.skills.all()],
        "education": [
            {
                "institution": ed.institution,
                "degree": ed.degree,
                "field_of_study": ed.field_of_study,
                "start_date": ed.start_date,
                "end_date": ed.end_date,
            }
            for ed in candidate.education.all()
        ],
        "experience": [
            {
                "company": ex.company,
                "title": ex.title,
                "start_date": ex.start_date,
                "end_date": ex.end_date,
                "is_current": ex.is_current,
            }
            for ex in candidate.experience.all()
        ],
        "overall_confidence": candidate.overall_confidence,
        "summary_one_liner": candidate.summary_one_liner,
    }


def _candidate_meets_requirements_llm(candidate: Candidate, requirements: dict) -> tuple[bool, list[str]]:
    """
    Use LLM to check if a candidate meets the specified requirements.
    More accurate than string matching, especially for role comparisons.
    Returns (meets_requirements: bool, reasons: list[str])
    """
    from .pipeline import call_requirements_validation
    
    candidate_data = _build_candidate_data_for_validation(candidate)
    
    try:
        result = call_requirements_validation(candidate_data, requirements)
        meets = result.get("meets_requirements", False)
        reasons = result.get("reasons", [])
        if not isinstance(reasons, list):
            reasons = [str(reasons)] if reasons else []
        return meets, reasons
    except Exception as e:
        # Fallback to string-based validation if LLM fails
        return _candidate_meets_requirements_string(candidate, requirements)


def _candidate_meets_requirements_string(candidate: Candidate, requirements: dict) -> tuple[bool, list[str]]:
    """
    String-based validation (fallback method).
    Less accurate but faster and doesn't require LLM call.
    """
    reasons = []
    meets = True
    
    # Check required skills (all must be present)
    if "required_skills" in requirements:
        required = [s.lower() for s in requirements["required_skills"]]
        candidate_skills = [s.name.lower() for s in candidate.skills.all()]
        missing = [s for s in required if s not in candidate_skills]
        if missing:
            meets = False
            reasons.append(f"Missing required skills: {', '.join(missing)}")
    
    # Check any skills (at least one must be present)
    if "any_skills" in requirements:
        any_skills = [s.lower() for s in requirements["any_skills"]]
        candidate_skills = [s.name.lower() for s in candidate.skills.all()]
        if not any(s in candidate_skills for s in any_skills):
            meets = False
            reasons.append(f"Missing at least one of these skills: {', '.join(requirements['any_skills'])}")
    
    # Check minimum years of experience
    if "min_years_experience" in requirements:
        years = _calculate_years_experience(candidate)
        if years < requirements["min_years_experience"]:
            meets = False
            reasons.append(f"Insufficient experience: {years:.1f} years (required: {requirements['min_years_experience']})")
    
    # Check required education degree
    if "required_education_degree" in requirements:
        required_degrees = [d.lower() for d in requirements["required_education_degree"]]
        candidate_degrees = [ed.degree.lower() if ed.degree else "" for ed in candidate.education.all()]
        if not any(degree and any(rd in degree.lower() for rd in required_degrees) for degree in candidate_degrees):
            meets = False
            reasons.append(f"Missing required education degree: {', '.join(requirements['required_education_degree'])}")
    
    # Check required primary role
    if "required_primary_role" in requirements:
        required_roles = [r.lower().strip() for r in requirements["required_primary_role"]]
        candidate_role = (candidate.primary_role or "").lower().strip()
        
        if not candidate_role:
            meets = False
            reasons.append(f"Primary role not found (required: {', '.join(requirements['required_primary_role'])})")
        else:
            # Strict matching: check if any required role is a substring of candidate role
            # OR if candidate role is a substring of any required role
            role_matches = any(
                required_role in candidate_role or candidate_role in required_role
                for required_role in required_roles
            )
            
            if not role_matches:
                meets = False
                reasons.append(f"Primary role mismatch: '{candidate.primary_role}' (required: {', '.join(requirements['required_primary_role'])})")
    
    # Check required seniority
    if "required_seniority" in requirements:
        required_seniorities = [s.lower() for s in requirements["required_seniority"]]
        candidate_seniority = (candidate.seniority or "").lower()
        if candidate_seniority not in required_seniorities:
            meets = False
            reasons.append(f"Seniority mismatch: '{candidate.seniority}' (required: {', '.join(requirements['required_seniority'])})")
    
    # Check location contains
    if "location_contains" in requirements:
        location_search = requirements["location_contains"].lower()
        candidate_location = (candidate.location or "").lower()
        if location_search not in candidate_location:
            meets = False
            reasons.append(f"Location mismatch: '{candidate.location}' (must contain: '{requirements['location_contains']}')")
    
    # Check minimum confidence
    if "min_confidence" in requirements:
        if candidate.overall_confidence < requirements["min_confidence"]:
            meets = False
            reasons.append(f"Low confidence: {candidate.overall_confidence:.2f} (required: {requirements['min_confidence']})")
    
    return meets, reasons


def _candidate_meets_requirements(candidate: Candidate, requirements: dict, use_llm: bool = True) -> tuple[bool, list[str]]:
    """
    Check if a candidate meets the specified requirements.
    Returns (meets_requirements: bool, reasons: list[str])
    
    Args:
        candidate: The candidate to check
        requirements: Dictionary of requirements to check against
        use_llm: If True, use LLM for semantic validation (more accurate but slower)
                 If False, use string-based validation (faster but less accurate)
    """
    if not requirements:
        return True, []
    
    # Check if LLM validation is requested (default: True for accuracy)
    if use_llm and requirements.get("use_llm_validation", True):
        return _candidate_meets_requirements_llm(candidate, requirements)
    else:
        return _candidate_meets_requirements_string(candidate, requirements)


class ResumeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    # Only allow list, retrieve, destroy (no create/update via this viewset)
    http_method_names = ['get', 'delete', 'head', 'options']

    def get_queryset(self):
        # (3) Ownership filtering
        return ResumeDocument.objects.filter(uploaded_by=self.request.user).order_by("-created_at")

    def destroy(self, request, *args, **kwargs):
        """Delete a resume document and all associated parse runs and candidates (cascade)."""
        instance = self.get_object()
        doc_id = instance.id
        filename = instance.original_filename
        
        # Count related objects before deletion (for logging)
        parse_runs_count = instance.parse_runs.count()
        candidates_count = instance.candidate_profiles.count()
        
        # Delete the file from filesystem if it exists
        if instance.file:
            try:
                instance.file.delete(save=False)
            except Exception as e:
                logger.warning(f"Failed to delete file for ResumeDocument {doc_id}: {e}")
        
        # Delete the document (cascade will delete parse_runs and candidates)
        instance.delete()
        
        logger.info(f"ResumeDocument {doc_id} deleted by user {request.user.id}", extra={
            "document_id": doc_id,
            "file_name": filename,
            "parse_runs_deleted": parse_runs_count,
            "candidates_deleted": candidates_count,
        })
        
        return ok(
            {
                "deleted_document": filename,
                "parse_runs_deleted": parse_runs_count,
                "candidates_deleted": candidates_count,
            },
            message=f"'{filename}' and all related data have been permanently deleted."
        )


class ParseRunViewSet(viewsets.ModelViewSet):
    serializer_class = ParseRunSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "parse_retry"
    # Only allow list, retrieve, destroy, and retry action (no create/update via this viewset)
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        # (3) Ownership filtering
        qs = ParseRun.objects.select_related("resume_document").filter(
            resume_document__uploaded_by=self.request.user
        ).order_by("-created_at")

        # Apply list filters from query params
        status = (self.request.query_params.get("status") or "").strip()
        if status:
            qs = qs.filter(status=status)

        after = (self.request.query_params.get("after") or "").strip()
        if after:
            try:
                after_date = datetime.strptime(after, "%Y-%m-%d").date()
                qs = qs.filter(created_at__date__gte=after_date)
            except ValueError:
                pass

        before = (self.request.query_params.get("before") or "").strip()
        if before:
            try:
                before_date = datetime.strptime(before, "%Y-%m-%d").date()
                qs = qs.filter(created_at__date__lte=before_date)
            except ValueError:
                pass

        return qs

    def destroy(self, request, *args, **kwargs):
        """Delete a parse run and its associated candidate (if any)."""
        instance = self.get_object()
        run_id = instance.id
        filename = instance.resume_document.original_filename if instance.resume_document else "Unknown"
        
        # Also delete associated candidate if exists
        from candidates.models import Candidate
        deleted_candidate = Candidate.objects.filter(parse_run=instance).delete()[0]
        
        instance.delete()
        logger.info(f"ParseRun {run_id} deleted by user {request.user.id}")
        
        return ok(
            {
                "deleted_parse_run": run_id,
                "deleted_candidate": deleted_candidate > 0,
            },
            message=f"Parse run for '{filename}' has been deleted." + (
                " The associated candidate profile was also removed." if deleted_candidate > 0 else ""
            )
        )

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """
        Retry parsing a resume that previously failed or had issues.
        Creates a new parse run with the latest model settings.
        """
        run = self.get_object()
        doc = run.resume_document

        if not doc.raw_text:
            return fail(
                "No text content available",
                code="NO_RAW_TEXT",
                status=400,
                user_message="This resume doesn't have any extractable text. Please upload a different file or check if the original file was valid."
            )

        new_run = ParseRun.objects.create(
            resume_document=doc,
            status="queued",
            model_name=getattr(settings, "OPENROUTER_EXTRACT_MODEL", "openai/gpt-4o-mini"),
            prompt_version="v1",
            temperature=float(getattr(settings, "OPENROUTER_TEMPERATURE", 0.1)),
        )

        # dispatch async, or sync if requested
        sync = request.query_params.get("sync") == "1"
        if getattr(settings, "RESUME_PARSE_ASYNC", True) and not sync:
            parse_resume_parse_run.delay(new_run.id)
            return ok(
                {"parse_run_id": new_run.id, "status": "queued"},
                status=202,
                message="Resume is being reprocessed. Check back shortly for the results."
            )

        # synchronous fallback
        parse_resume_parse_run(new_run.id)
        new_run.refresh_from_db()
        
        status_messages = {
            'success': "Resume successfully reprocessed! The candidate profile has been updated.",
            'partial': "Resume reprocessed with some missing information. Please review the results.",
            'failed': "Unfortunately, we couldn't process this resume. Please try a different file format.",
        }
        
        return ok(
            ParseRunSerializer(new_run).data,
            status=201,
            message=status_messages.get(new_run.status, "Resume processing complete.")
        )


class ResumeUploadViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "resumes_upload"

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        ser = ResumeUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        f = ser.validated_data["file"]

        # Get requirements from request data (JSON field) - support for single file upload
        requirements_json = request.data.get("requirements")
        if requirements_json and isinstance(requirements_json, str):
            import json
            try:
                requirements_json = json.loads(requirements_json)
            except json.JSONDecodeError:
                return fail(
                    "Invalid JSON in requirements",
                    code="INVALID_REQUIREMENTS",
                    status=400,
                    user_message="The filter criteria you provided isn't valid JSON. Please check the format and try again."
                )
        
        # Validate requirements if provided
        requirements = None
        if requirements_json:
            from .serializers import BulkResumeUploadSerializer
            temp_ser = BulkResumeUploadSerializer(data={"files": [f], "requirements": requirements_json})
            if temp_ser.is_valid():
                requirements = temp_ser.validated_data.get("requirements")
            else:
                # Extract user-friendly error message
                req_errors = temp_ser.errors.get("requirements", [])
                error_msg = req_errors[0] if req_errors else "Invalid filter criteria"
                return fail(
                    f"Invalid requirements: {temp_ser.errors}",
                    code="INVALID_REQUIREMENTS",
                    status=400,
                    user_message=str(error_msg)
                )

        # (2) Idempotency: compute hash and check duplicates per user
        file_hash = sha256_of_uploaded_file(f)
        existing = ResumeDocument.objects.filter(uploaded_by=request.user, file_hash=file_hash).first()
        if existing:
            latest_candidate = Candidate.objects.filter(resume_document=existing).order_by("-created_at").first()
            latest_run = existing.parse_runs.order_by("-created_at").first()
            
            # Check requirements for duplicates too (sync mode only)
            if requirements and latest_candidate:
                sync = request.query_params.get("sync") == "1"
                if sync:
                    meets, reasons = _candidate_meets_requirements(latest_candidate, requirements)
                    if not meets:
                        return ok({
                            "duplicate": True,
                            "resume_document_id": existing.id,
                            "parse_run_id": latest_run.id if latest_run else None,
                            "candidate_id": latest_candidate.id if latest_candidate else None,
                            "status": latest_run.status if latest_run else None,
                            "requirements_check": "failed",
                            "rejection_reasons": reasons,
                        }, status=200)
            
            return ok({
                "duplicate": True,
                "resume_document_id": existing.id,
                "parse_run_id": latest_run.id if latest_run else None,
                "candidate_id": latest_candidate.id if latest_candidate else None,
                "status": latest_run.status if latest_run else None,
            }, status=200)

        # Save document
        doc = ResumeDocument.objects.create(
            original_filename=f.name,
            file=f,
            mime_type=getattr(f, "content_type", "") or "",
            file_hash=file_hash,
            file_size=getattr(f, "size", 0) or 0,
            uploaded_by=request.user,
        )

        # Extraction is now handled in the async task
        logger.info("Scheduling extraction task", extra={"document_id": doc.id, "file_name": doc.original_filename})

        # Create ParseRun queued and dispatch (7)
        run = ParseRun.objects.create(
            resume_document=doc,
            status="queued",
            model_name=getattr(settings, "OPENROUTER_EXTRACT_MODEL", "openai/gpt-4o-mini"),
            prompt_version="v1",
            temperature=float(getattr(settings, "OPENROUTER_TEMPERATURE", 0.1)),
            requirements=requirements,  # Store requirements if provided
        )

        sync = request.query_params.get("sync") == "1"
        if getattr(settings, "RESUME_PARSE_ASYNC", True) and not sync:
            parse_resume_parse_run.delay(run.id, requirements=requirements)
            return ok(
                {"resume_document_id": doc.id, "parse_run_id": run.id, "status": "queued"},
                status=202,
                message="Resume uploaded successfully! Processing has started and will complete shortly."
            )

        # sync fallback for demos/testing
        parse_resume_parse_run(run.id)
        run.refresh_from_db()
        latest_candidate = Candidate.objects.filter(parse_run=run).order_by("-created_at").first()
        
        # Check requirements if provided (sync mode only)
        rejected = False
        rejection_reasons = []
        if requirements and latest_candidate:
            meets, reasons = _candidate_meets_requirements(latest_candidate, requirements)
            if not meets:
                rejected = True
                rejection_reasons = reasons
                latest_candidate.delete()  # Discard candidate that doesn't meet requirements
                latest_candidate = None
        
        response_data = {
            "resume_document_id": doc.id,
            "parse_run_id": run.id,
            "status": run.status,
            "candidate_id": latest_candidate.id if latest_candidate else None,
        }
        
        if requirements:
            response_data["requirements_applied"] = requirements
            if run.status == "rejected" or rejected:
                response_data["rejected"] = True
                response_data["status"] = "rejected"
                # Get reasons from run warnings if task failed
                reasons = []
                if rejected: 
                    reasons = rejection_reasons
                elif isinstance(run.warnings, list):
                    for w in run.warnings:
                        if w.startswith("REQUIREMENTS_FAILED: "):
                            reasons.append(w.replace("REQUIREMENTS_FAILED: ", ""))
                
                response_data["rejection_reasons"] = reasons
            else:
                response_data["accepted"] = True
        
        return ok(response_data, status=201)

    @action(detail=False, methods=["post"], url_path="bulk-upload")
    def bulk_upload(self, request):
        """
        Bulk upload endpoint that accepts multiple files.
        Returns a summary of all uploads with their status.
        """
        # Handle both 'files' (list) and 'file' (multiple files with same name)
        files = request.FILES.getlist("files") or request.FILES.getlist("file")
        
        if not files:
            return fail(
                "No files provided",
                code="NO_FILES",
                status=400,
                user_message="Please select at least one resume file to upload."
            )
        
        if len(files) > 100:
            return fail(
                "Too many files",
                code="TOO_MANY_FILES",
                status=400,
                user_message=f"You've selected {len(files)} files, but the maximum is 100. Please split your upload into smaller batches."
            )

        # Get requirements from request data (JSON field)
        requirements_json = request.data.get("requirements")
        if requirements_json and isinstance(requirements_json, str):
            import json
            try:
                requirements_json = json.loads(requirements_json)
            except json.JSONDecodeError:
                return fail(
                    "Invalid JSON in requirements",
                    code="INVALID_REQUIREMENTS",
                    status=400,
                    user_message="The filter criteria format is invalid. Please use valid JSON format."
                )

        ser = BulkResumeUploadSerializer(data={"files": files, "requirements": requirements_json})
        ser.is_valid(raise_exception=True)
        validated_files = ser.validated_data["files"]
        requirements = ser.validated_data.get("requirements")

        sync = request.query_params.get("sync") == "1"
        results = []
        errors = []
        discarded = []  # Candidates that don't meet requirements

        for idx, f in enumerate(validated_files):
            try:
                # Idempotency: compute hash and check duplicates per user
                file_hash = sha256_of_uploaded_file(f)
                existing = ResumeDocument.objects.filter(uploaded_by=request.user, file_hash=file_hash).first()
                
                if existing:
                    latest_candidate = Candidate.objects.filter(resume_document=existing).order_by("-created_at").first()
                    latest_run = existing.parse_runs.order_by("-created_at").first()
                    
                    # Check requirements for duplicates too (sync mode only)
                    if requirements and latest_candidate and sync:
                        meets, reasons = _candidate_meets_requirements(latest_candidate, requirements)
                        if not meets:
                            discarded.append({
                                "filename": f.name,
                                "candidate_id": latest_candidate.id,
                                "reasons": reasons,
                                "duplicate": True,
                            })
                            results.append({
                                "filename": f.name,
                                "duplicate": True,
                                "resume_document_id": existing.id,
                                "parse_run_id": latest_run.id if latest_run else None,
                                "candidate_id": latest_candidate.id if latest_candidate else None,
                                "status": latest_run.status if latest_run else None,
                                "discarded": True,
                                "discard_reasons": reasons,
                            })
                            continue
                    
                    # If duplicate meets requirements or no requirements, add to results
                    results.append({
                        "filename": f.name,
                        "duplicate": True,
                        "resume_document_id": existing.id,
                        "parse_run_id": latest_run.id if latest_run else None,
                        "candidate_id": latest_candidate.id if latest_candidate else None,
                        "status": latest_run.status if latest_run else None,
                    })
                    continue

                # Save document
                doc = ResumeDocument.objects.create(
                    original_filename=f.name,
                    file=f,
                    mime_type=getattr(f, "content_type", "") or "",
                    file_hash=file_hash,
                    file_size=getattr(f, "size", 0) or 0,
                    uploaded_by=request.user,
                )

                # Extraction is now handled in the async task
                logger.info("Scheduling extraction task", extra={"document_id": doc.id, "file_name": doc.original_filename})

                # Create ParseRun queued and dispatch
                run = ParseRun.objects.create(
                    resume_document=doc,
                    status="queued",
                    model_name=getattr(settings, "OPENROUTER_EXTRACT_MODEL", "openai/gpt-4o-mini"),
                    prompt_version="v1",
                    temperature=float(getattr(settings, "OPENROUTER_TEMPERATURE", 0.1)),
                    requirements=requirements,  # Store requirements for async checking
                )

                if getattr(settings, "RESUME_PARSE_ASYNC", True) and not sync:
                    parse_resume_parse_run.delay(run.id, requirements=requirements)
                    results.append({
                        "filename": f.name,
                        "resume_document_id": doc.id,
                        "parse_run_id": run.id,
                        "status": "queued",
                        "requirements_check_pending": bool(requirements),  # Will check after async processing
                    })
                else:
                    # sync fallback for demos/testing
                    parse_resume_parse_run(run.id)
                    run.refresh_from_db()
                    latest_candidate = Candidate.objects.filter(parse_run=run).order_by("-created_at").first()
                    
                    # If task didn't discard but view should (legacy/safety), or if task ALREADY discarded
                    if (requirements and latest_candidate and not _candidate_meets_requirements(latest_candidate, requirements)[0]) or (run.status == "rejected"):
                        reasons = []
                        if run.status == "rejected" and isinstance(run.warnings, list):
                            for w in run.warnings:
                                if w.startswith("REQUIREMENTS_FAILED: "):
                                    reasons.append(w.replace("REQUIREMENTS_FAILED: ", ""))
                        
                        if not reasons and latest_candidate:
                            # Re-check if not found in status
                            meets, reasons = _candidate_meets_requirements(latest_candidate, requirements)
                        
                        results.append({
                            "filename": f.name,
                            "resume_document_id": doc.id,
                            "parse_run_id": run.id,
                            "status": "rejected",
                            "discarded": True,
                            "discard_reasons": reasons,
                        })
                        if latest_candidate:
                            latest_candidate.delete()
                        continue
                    
                    results.append({
                        "filename": f.name,
                        "resume_document_id": doc.id,
                        "parse_run_id": run.id,
                        "status": run.status,
                        "candidate_id": latest_candidate.id if latest_candidate else None,
                    })

            except Exception as e:
                errors.append({
                    "filename": f.name,
                    "error": str(e),
                    "error_code": "UPLOAD_FAILED",
                })

        # Include all results with clear status indicators
        all_results = []
        for r in results:
            if r.get("discarded", False):
                r["status_type"] = "rejected"
                r["accepted"] = False
            elif r.get("duplicate", False):
                r["status_type"] = "duplicate"
                r["accepted"] = True  # Duplicates are considered accepted
            elif r.get("candidate_id"):
                r["status_type"] = "accepted"
                r["accepted"] = True
            else:
                r["status_type"] = "processed"
                r["accepted"] = True
            
            all_results.append(r)
        
        summary = {
            "total": len(validated_files),
            "successful": len(results),
            "matching": len([r for r in all_results if r.get("accepted", False) and not r.get("discarded", False)]),
            "rejected_count": len([r for r in all_results if r.get("discarded", False)]),
            "error_count": len(errors),
            "results": all_results,
            "accepted_list": [r for r in all_results if r.get("accepted", False) and not r.get("discarded", False)],
            "rejected_list": [r for r in all_results if r.get("discarded", False)],
            "errors": errors,
        }
        
        if discarded:
            summary["discarded_details"] = discarded
        
        if requirements:
            summary["requirements_applied"] = requirements
            if sync:
                summary["note"] = f"Requirements applied. {summary['matching']} candidates accepted, {summary['rejected_count']} rejected."
            else:
                summary["note"] = "Requirements will be checked after async processing completes. Check parse runs for final status."

        status_code = 202 if getattr(settings, "RESUME_PARSE_ASYNC", True) and not sync else 201
        return ok(summary, status=status_code)
