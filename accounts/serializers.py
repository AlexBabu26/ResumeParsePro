from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    """
    User registration serializer with user-friendly validation messages.
    """
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        error_messages={
            'min_length': 'Password must be at least 8 characters long.',
            'required': 'Please enter a password.',
        }
    )
    password2 = serializers.CharField(
        write_only=True, 
        min_length=8,
        error_messages={
            'min_length': 'Password confirmation must be at least 8 characters long.',
            'required': 'Please confirm your password.',
        }
    )
    email = serializers.EmailField(
        required=True,
        error_messages={
            'invalid': 'Please enter a valid email address.',
            'required': 'Email address is required.',
        }
    )
    username = serializers.CharField(
        error_messages={
            'required': 'Please choose a username.',
        }
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "password2")

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken. Please choose a different one.")
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long.")
        if not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError("Username can only contain letters, numbers, underscores, and hyphens.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists. Try logging in instead.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords don't match. Please make sure both passwords are identical."})
        
        try:
            validate_password(attrs["password"])
        except ValidationError as e:
            # Convert Django's validation errors to user-friendly messages
            messages = list(e.messages)
            raise serializers.ValidationError({"password": messages[0] if messages else "Password doesn't meet security requirements."})
        
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Forgot password serializer - finds user by username or email.
    """
    username_or_email = serializers.CharField(
        required=True,
        error_messages={
            'required': 'Please enter your username or email address.',
        }
    )

    def validate_username_or_email(self, value):
        """Check if username or email exists and store user in context"""
        value = value.strip()
        user = None
        
        # Try to find by username first
        try:
            user = User.objects.get(username__iexact=value)
        except User.DoesNotExist:
            pass
        
        # If not found, try email
        if not user:
            try:
                user = User.objects.get(email__iexact=value)
            except User.DoesNotExist:
                pass
        
        if not user:
            raise serializers.ValidationError(
                "We couldn't find an account with that username or email. "
                "Please check your spelling and try again."
            )
        
        # Store user in serializer context for later use
        self.user = user
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """
    Password reset serializer with user-friendly validation.
    """
    user_id = serializers.IntegerField(required=True)
    password = serializers.CharField(
        write_only=True, 
        min_length=8, 
        required=True,
        error_messages={
            'min_length': 'Your new password must be at least 8 characters long.',
            'required': 'Please enter a new password.',
        }
    )
    password2 = serializers.CharField(
        write_only=True, 
        min_length=8, 
        required=True,
        error_messages={
            'min_length': 'Password confirmation must be at least 8 characters long.',
            'required': 'Please confirm your new password.',
        }
    )

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({
                "password": "Passwords don't match. Please make sure both passwords are identical."
            })
        
        try:
            validate_password(attrs["password"])
        except ValidationError as e:
            messages = list(e.messages)
            raise serializers.ValidationError({
                "password": messages[0] if messages else "Password doesn't meet security requirements."
            })
        
        return attrs

    def validate_user_id(self, value):
        """Check if user exists"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "We couldn't find your account. Please request a new password reset."
            )
        return value

    def save(self):
        user_id = self.validated_data["user_id"]
        password = self.validated_data["password"]
        user = User.objects.get(id=user_id)
        user.set_password(password)
        user.save()
        return user
