# core/responses.py
from rest_framework.response import Response


def ok(data=None, status=200):
    return Response({"success": True, "data": data, "error": None}, status=status)


def fail(message: str, code: str = "ERROR", status: int = 400, details=None):
    return Response(
        {"success": False, "data": None, "error": {"code": code, "message": message, "details": details}},
        status=status,
    )

