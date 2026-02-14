from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from core.responses import ok, fail
from .serializers import RegisterSerializer, ForgotPasswordSerializer, ResetPasswordSerializer


class RegisterView(generics.CreateAPIView):
    """
    Register a new user account.
    
    Requires: username, email, password, password2 (confirmation)
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return ok(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
                status=201,
                message="Account created successfully! You can now log in with your credentials."
            )
        
        # Format validation errors in a user-friendly way
        errors = serializer.errors
        if "username" in errors:
            if "unique" in str(errors["username"]).lower():
                return fail(
                    "Username already taken",
                    code="VALIDATION_ERROR",
                    status=400,
                    user_message="This username is already taken. Please choose a different one."
                )
        if "email" in errors:
            if "unique" in str(errors["email"]).lower():
                return fail(
                    "Email already registered",
                    code="VALIDATION_ERROR", 
                    status=400,
                    user_message="An account with this email already exists. Try logging in instead."
                )
        if "password" in errors:
            return fail(
                str(errors["password"][0]),
                code="VALIDATION_ERROR",
                status=400,
                user_message=str(errors["password"][0])  # Django's password validators have good messages
            )
        
        # Generic validation error
        return fail(
            "Validation failed",
            code="VALIDATION_ERROR",
            status=400,
            user_message="Please check your information and try again.",
            details=errors
        )


class ForgotPasswordView(APIView):
    """
    Request a password reset by providing username or email.
    
    In production, this would send a reset email with a secure token.
    For this demo, it returns a user_id for the reset endpoint.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.user
            return ok(
                {
                    "user_id": user.id,
                    "email_hint": f"{user.email[:2]}***{user.email[user.email.find('@'):]}" if user.email else None,
                },
                message="We found your account. You can now reset your password."
            )
        
        # User not found - give a helpful message
        return fail(
            "User not found",
            code="NOT_FOUND",
            status=404,
            user_message="We couldn't find an account with that username or email. Please check and try again."
        )


class ResetPasswordView(APIView):
    """
    Reset user password with a new password.
    
    Requires: user_id, password, password2 (confirmation)
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return ok(
                None,
                message="Your password has been reset successfully. You can now log in with your new password."
            )
        
        errors = serializer.errors
        if "password" in errors:
            # Password validation errors (too common, too short, etc.)
            error_msg = str(errors["password"][0])
            return fail(
                error_msg,
                code="VALIDATION_ERROR",
                status=400,
                user_message=error_msg
            )
        if "user_id" in errors:
            return fail(
                "Invalid user",
                code="NOT_FOUND",
                status=404,
                user_message="We couldn't find your account. Please request a new password reset."
            )
        
        return fail(
            "Validation failed",
            code="VALIDATION_ERROR",
            status=400,
            user_message="Please make sure both passwords match and meet the requirements.",
            details=errors
        )
