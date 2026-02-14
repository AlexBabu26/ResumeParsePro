# core/responses.py
"""
Standardized API response helpers for Parse Pro AI.

All API responses follow a consistent structure:
{
    "success": true/false,
    "data": { ... } or null,
    "error": { "code": "...", "message": "...", "details": ... } or null
}

User-friendly messages are prioritized over technical jargon.
"""
from rest_framework.response import Response


# =============================================================================
# USER-FRIENDLY ERROR MESSAGES
# =============================================================================
# Maps internal error codes to user-friendly messages
ERROR_MESSAGES = {
    # File Upload Errors
    "NO_FILES": "Please select at least one file to upload.",
    "TOO_MANY_FILES": "You can upload a maximum of 100 files at once. Please split your files into smaller batches.",
    "INVALID_FILE_TYPE": "This file type is not supported. Please upload a PDF or Word document (.pdf, .docx).",
    "FILE_TOO_LARGE": "This file is too large. Please upload a file smaller than 10MB.",
    "EMPTY_FILE": "This file appears to be empty. Please check the file and try again.",
    
    # Text Extraction Errors
    "TEXT_EXTRACTION_FAILED": "We couldn't read the content from this file. Please make sure the file isn't corrupted and try again.",
    "PASSWORD_PROTECTED": "This PDF is password-protected. Please remove the password and upload again.",
    "CORRUPTED_PDF": "This PDF file appears to be damaged. Please try saving it again or use a different version.",
    "CORRUPTED_DOCX": "This Word document appears to be damaged. Please try saving it again or use a different version.",
    "PDF_EXTRACTION_ERROR": "We had trouble reading this PDF. Please try converting it to a Word document.",
    "DOCX_EXTRACTION_ERROR": "We had trouble reading this Word document. Please try saving it as a PDF instead.",
    "DOC_EXTRACTION_ERROR": "This is an older Word format (.doc). Please save it as .docx or PDF for better results.",
    "TXT_READ_ERROR": "We couldn't read this text file. Please check if it contains valid text.",
    "MISSING_DEPENDENCY": "A required system component is missing. Please contact support.",
    
    # Parsing Errors
    "NO_RAW_TEXT": "We couldn't extract any text from this resume. The file might be image-based or empty.",
    "LLM_INVALID_JSON": "We had trouble processing this resume. Please try again or upload a cleaner version.",
    "LLM_TIMEOUT": "Processing took too long. Please try again in a few moments.",
    "LLM_ERROR": "We encountered an issue while analyzing the resume. Please try again.",
    "PARSE_FAILED": "Resume parsing failed. Please check if the file contains readable text.",
    
    # Rate Limit Errors
    "RATE_LIMIT": "You've made too many requests. Please wait a few minutes before trying again.",
    "DAILY_LIMIT_EXCEEDED": "You've reached your daily limit. Please try again tomorrow or upgrade your plan.",
    
    # Authentication Errors
    "AUTH_ERROR": "Your session has expired. Please log in again.",
    "INVALID_CREDENTIALS": "The username or password you entered is incorrect.",
    "ACCOUNT_DISABLED": "Your account has been disabled. Please contact support.",
    
    # Requirements Validation Errors
    "INVALID_REQUIREMENTS": "The filter criteria you provided is invalid. Please check the format and try again.",
    "REQUIREMENTS_FAILED": "This candidate doesn't match your specified criteria.",
    
    # General Errors
    "NOT_FOUND": "The item you're looking for doesn't exist or has been deleted.",
    "PERMISSION_DENIED": "You don't have permission to access this resource.",
    "VALIDATION_ERROR": "Please check your input and try again.",
    "SERVER_ERROR": "Something went wrong on our end. Please try again later.",
    "NETWORK_ERROR": "We're having trouble connecting to our AI service. Please try again in a moment.",
    "TIMEOUT": "The request timed out. Please try again.",
    "ERROR": "An unexpected error occurred. Please try again.",
}

# Success message templates
SUCCESS_MESSAGES = {
    "UPLOAD_SUCCESS": "Resume uploaded successfully! Processing will begin shortly.",
    "UPLOAD_QUEUED": "Resume uploaded and queued for processing. You'll see results soon.",
    "PARSE_SUCCESS": "Resume processed successfully!",
    "CANDIDATE_CREATED": "Candidate profile created successfully.",
    "CANDIDATE_UPDATED": "Candidate profile updated successfully.",
    "CANDIDATE_DELETED": "Candidate profile deleted successfully.",
    "DOCUMENT_DELETED": "Document and all related data deleted successfully.",
    "EXPORT_SUCCESS": "Export completed successfully.",
    "PASSWORD_RESET": "Your password has been reset successfully. You can now log in.",
    "REGISTRATION_SUCCESS": "Account created successfully! You can now log in.",
    "DUPLICATE_FOUND": "This resume was already uploaded. Showing the existing record.",
}


def ok(data=None, status=200, message=None):
    """
    Return a successful API response.
    
    Args:
        data: The response data (dict, list, or None)
        status: HTTP status code (default: 200)
        message: Optional success message for the user
    """
    response_data = {
        "success": True,
        "data": data,
        "error": None,
    }
    if message:
        response_data["message"] = message
    return Response(response_data, status=status)


def fail(message: str, code: str = "ERROR", status: int = 400, details=None, user_message: str = None):
    """
    Return an error API response with user-friendly messaging.
    
    Args:
        message: Technical error message (for logging/debugging)
        code: Error code for programmatic handling
        status: HTTP status code (default: 400)
        details: Additional error details
        user_message: Override the default user-friendly message
    """
    # Get user-friendly message from our mapping, or use provided user_message
    friendly_message = user_message or ERROR_MESSAGES.get(code, message)
    
    return Response(
        {
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": friendly_message,
                "details": details,
            }
        },
        status=status,
    )


def get_user_message(code: str, default: str = None) -> str:
    """Get a user-friendly message for an error code."""
    return ERROR_MESSAGES.get(code, default or "An error occurred.")


def get_success_message(code: str, default: str = None) -> str:
    """Get a success message template."""
    return SUCCESS_MESSAGES.get(code, default or "Operation completed successfully.")

