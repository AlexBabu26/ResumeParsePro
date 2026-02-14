import logging
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded, Retry
from django.db import transaction
from django.utils import timezone
import requests

from .models import ParseRun, ParseRunStatusLog
from .pipeline import (
    extract_known_pii, 
    call_extract, 
    normalize_and_validate, 
    enrich_with_classification_and_summary,
    check_rate_limit_status,
)
from .extraction import extract_text_from_file, clean_text, ExtractionError
from .services import persist_candidate_from_normalized
from candidates.models import Candidate

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when OpenRouter rate limit is exhausted."""
    pass


def _update_status(run: ParseRun, new_status: str, reason: str = None):
    """Update ParseRun status and log the change."""
    old_status = run.status
    run.status = new_status
    run.save(update_fields=["status", "updated_at"])
    
    # Log status change
    ParseRunStatusLog.objects.create(
        parse_run=run,
        old_status=old_status,
        new_status=new_status,
        reason=reason
    )
    logger.info(f"ParseRun {run.id} status: {old_status} -> {new_status}", extra={
        "parse_run_id": run.id,
        "old_status": old_status,
        "new_status": new_status,
        "reason": reason
    })


def _update_progress(run: ParseRun, stage: str):
    """Update progress stage for tracking."""
    run.progress_stage = stage
    run.save(update_fields=["progress_stage", "updated_at"])
    logger.debug(f"ParseRun {run.id} progress: {stage}", extra={
        "parse_run_id": run.id,
        "progress_stage": stage
    })


@shared_task(
    bind=True,
    max_retries=5,  # Increased for rate limit resilience
    default_retry_delay=60,  # 1 minute default delay for rate limits
    autoretry_for=(requests.Timeout, requests.ConnectionError),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minute backoff for rate limits
    retry_jitter=True,
    soft_time_limit=240,
    time_limit=300,
)
def parse_resume_parse_run(self, parse_run_id: int, requirements: dict = None):
    """
    Main Celery task for parsing a resume.
    
    Features:
    - Exponential backoff retry for transient errors
    - Rate limit awareness for free tier OpenRouter
    - Progress stage tracking
    - Status change logging
    - Soft/hard time limits
    - Model fallbacks for rate limit resilience
    """
    logger.info(f"Starting parse task for ParseRun {parse_run_id}", extra={
        "parse_run_id": parse_run_id,
        "task_id": self.request.id,
        "retry_count": self.request.retries,
    })
    
    try:
        run = ParseRun.objects.select_related("resume_document").get(id=parse_run_id)
    except ParseRun.DoesNotExist:
        logger.error(f"ParseRun {parse_run_id} not found", extra={"parse_run_id": parse_run_id})
        return
    
    doc = run.resume_document
    
    # Track retry count
    run.retry_count = self.request.retries
    run.task_started_at = timezone.now()
    run.save(update_fields=["retry_count", "task_started_at", "updated_at"])
    
    # Get requirements from ParseRun if not passed directly
    if requirements is None:
        requirements = run.requirements

    # Check rate limit status before processing (free tier optimization)
    try:
        rate_status = check_rate_limit_status()
        if rate_status.get("limit_remaining") == 0:
            logger.warning(f"ParseRun {parse_run_id} rate limit exhausted, scheduling retry", extra={
                "parse_run_id": parse_run_id,
                "usage_daily": rate_status.get("usage_daily"),
                "is_free_tier": rate_status.get("is_free_tier"),
            })
            # Retry after 5 minutes for rate limit exhaustion
            raise self.retry(countdown=300, exc=RateLimitExceeded("Daily rate limit exhausted"))
    except RateLimitExceeded:
        raise  # Re-raise to trigger Celery retry
    except Exception as e:
        # Don't fail the task if rate limit check fails, just log and continue
        logger.debug(f"Rate limit check failed (continuing): {e}")

    try:
        _update_status(run, "processing", "Task started")

        if not doc.raw_text:
            # Attempt extraction within the task if not done yet
            try:
                _update_progress(run, "extracting_text")
                raw, method = extract_text_from_file(doc.file.path, doc.mime_type, doc.original_filename)
                doc.raw_text = clean_text(raw)
                doc.extraction_method = method
                doc.save(update_fields=["raw_text", "extraction_method", "updated_at"])
                logger.info(f"ParseRun {run.id} text extraction complete", extra={
                    "parse_run_id": run.id,
                    "extraction_method": method,
                    "text_length": len(doc.raw_text),
                })
            except Exception as e:
                _update_status(run, "failed", f"Text extraction failed: {str(e)}")
                run.error_code = "TEXT_EXTRACTION_FAILED"
                run.error_message = str(e)
                run.task_completed_at = timezone.now()
                run.save(update_fields=["error_code", "error_message", "task_completed_at", "updated_at"])
                logger.warning(f"ParseRun {run.id} failed: text extraction error", extra={"parse_run_id": run.id, "error": str(e)})
                return

        if not doc.raw_text:
            _update_status(run, "failed", "No raw text available after extraction attempt")
            run.error_code = "NO_RAW_TEXT"
            run.error_message = "No raw text extracted from document."
            run.task_completed_at = timezone.now()
            run.save(update_fields=["error_code", "error_message", "task_completed_at", "updated_at"])
            logger.warning(f"ParseRun {run.id} failed: no raw text", extra={"parse_run_id": run.id})
            return

        # Stage 1: Extract PII
        _update_progress(run, "extracting_pii")
        known_pii = extract_known_pii(doc.raw_text)
        logger.info(f"ParseRun {run.id} PII extracted", extra={
            "parse_run_id": run.id,
            "emails_found": len(known_pii.get("emails_found", [])),
            "phones_found": len(known_pii.get("phones_found", [])),
            "links_found": len(known_pii.get("links_found", [])),
        })

        # Stage 2: Call LLM for extraction
        _update_progress(run, "calling_llm")
        llm = call_extract(doc.raw_text, known_pii)
        run.llm_raw_json = llm["parsed_json"]
        run.latency_ms = llm["latency_ms"]
        run.input_tokens = llm.get("input_tokens")
        run.output_tokens = llm.get("output_tokens")
        run.model_name = llm["model"]
        run.save(update_fields=["llm_raw_json", "latency_ms", "input_tokens", "output_tokens", "model_name", "updated_at"])
        
        logger.info(f"ParseRun {run.id} LLM extraction complete", extra={
            "parse_run_id": run.id,
            "model": llm["model"],
            "latency_ms": llm["latency_ms"],
            "input_tokens": llm.get("input_tokens"),
            "output_tokens": llm.get("output_tokens"),
        })

        # Stage 3: Validate and normalize
        _update_progress(run, "validating")
        normalized, warnings, missing, status_out = normalize_and_validate(llm["parsed_json"], doc.raw_text, known_pii)
        logger.info(f"ParseRun {run.id} validation complete", extra={
            "parse_run_id": run.id,
            "status": status_out,
            "warnings_count": len(warnings),
            "missing_fields": missing,
        })

        # Stage 4 & 5: Classification and summary (if extraction was successful)
        if status_out in {"success", "partial"}:
            _update_progress(run, "classifying")
            normalized, warnings = enrich_with_classification_and_summary(normalized)
            _update_progress(run, "summarizing")

        run.normalized_json = normalized
        run.warnings = warnings
        
        # Stage 6: Persist candidate
        _update_progress(run, "persisting")
        with transaction.atomic():
            candidate_id = persist_candidate_from_normalized(doc, run, normalized)
            logger.info(f"ParseRun {run.id} candidate persisted", extra={
                "parse_run_id": run.id,
                "candidate_id": candidate_id,
            })
            
            # Check requirements after candidate is created (async mode)
            if requirements:
                from .requirements_helpers import _candidate_meets_requirements
                candidate = Candidate.objects.get(id=candidate_id)
                meets, reasons = _candidate_meets_requirements(candidate, requirements)
                if not meets:
                    # Discard candidate that doesn't meet requirements
                    candidate.delete()  # This will cascade delete skills, education, experience
                    # Update warnings to include rejection reason
                    if not isinstance(run.warnings, list):
                        run.warnings = []
                    run.warnings.append(f"REQUIREMENTS_FAILED: {', '.join(reasons)}")
                    # Set status to rejected instead of success
                    status_out = "rejected"
                    logger.info(f"ParseRun {run.id} candidate rejected", extra={
                        "parse_run_id": run.id,
                        "candidate_id": candidate_id,
                        "rejection_reasons": reasons,
                    })

        # Mark complete
        _update_progress(run, "complete")
        _update_status(run, status_out, "Pipeline completed successfully")
        run.task_completed_at = timezone.now()
        run.save(update_fields=["normalized_json", "warnings", "task_completed_at", "updated_at"])
        
        logger.info(f"ParseRun {run.id} completed successfully", extra={
            "parse_run_id": run.id,
            "final_status": status_out,
            "duration_ms": run.latency_ms,
        })

    except SoftTimeLimitExceeded:
        _update_status(run, "failed", "Task exceeded soft time limit")
        run.error_code = "TIMEOUT"
        run.error_message = "Task exceeded time limit (4 minutes)"
        run.task_completed_at = timezone.now()
        run.save(update_fields=["error_code", "error_message", "task_completed_at", "updated_at"])
        logger.error(f"ParseRun {run.id} timed out", extra={"parse_run_id": run.id})
        # Don't retry on timeout - it's likely a systematic issue
        
    except RateLimitExceeded as e:
        # Rate limit exhausted - schedule retry with longer delay
        logger.warning(f"ParseRun {run.id} rate limit exceeded (will retry)", extra={
            "parse_run_id": run.id,
            "error": str(e),
            "retry_count": self.request.retries,
        })
        run.error_code = "RATE_LIMIT"
        run.error_message = f"Rate limit exceeded: {str(e)}"
        run.save(update_fields=["error_code", "error_message", "updated_at"])
        raise  # Let Celery retry with backoff
        
    except (requests.Timeout, requests.ConnectionError) as e:
        # These are retryable errors - let Celery handle the retry
        error_str = str(e)
        
        # Check if this is a rate limit error (429)
        if "429" in error_str or "Rate limited" in error_str:
            logger.warning(f"ParseRun {run.id} rate limited (will retry with backoff)", extra={
                "parse_run_id": run.id,
                "error": error_str,
                "retry_count": self.request.retries,
            })
            run.error_code = "RATE_LIMIT"
            run.error_message = f"Rate limited: {error_str}"
            run.save(update_fields=["error_code", "error_message", "updated_at"])
            # Use longer countdown for rate limit errors
            raise self.retry(countdown=120 * (self.request.retries + 1), exc=e)
        
        logger.warning(f"ParseRun {run.id} network error (will retry)", extra={
            "parse_run_id": run.id,
            "error": error_str,
            "retry_count": self.request.retries,
        })
        run.error_code = "NETWORK_ERROR"
        run.error_message = f"Network error: {error_str}"
        run.save(update_fields=["error_code", "error_message", "updated_at"])
        raise  # Let Celery retry
        
    except RuntimeError as e:
        error_str = str(e)
        # Check for non-retryable API errors
        if "401" in error_str or "403" in error_str:
            _update_status(run, "failed", "API authentication error")
            run.error_code = "AUTH_ERROR"
            run.error_message = error_str
            run.task_completed_at = timezone.now()
            run.save(update_fields=["error_code", "error_message", "task_completed_at", "updated_at"])
            logger.error(f"ParseRun {run.id} auth error", extra={
                "parse_run_id": run.id,
                "error": error_str
            })
            return  # Don't retry auth errors
        
        # Other runtime errors may be retryable
        logger.warning(f"ParseRun {run.id} runtime error", extra={
            "parse_run_id": run.id,
            "error": error_str,
        })
        run.error_code = "RUNTIME_ERROR"
        run.error_message = error_str
        run.save(update_fields=["error_code", "error_message", "updated_at"])
        raise  # Let Celery decide on retry
        
    except Exception as e:
        _update_status(run, "failed", f"Pipeline error: {str(e)}")
        run.error_code = "PIPELINE_FAILED"
        run.error_message = str(e)
        run.task_completed_at = timezone.now()
        run.save(update_fields=["error_code", "error_message", "task_completed_at", "updated_at"])
        logger.exception(f"ParseRun {run.id} unexpected error", extra={
            "parse_run_id": run.id,
            "error": str(e),
        })
        raise

