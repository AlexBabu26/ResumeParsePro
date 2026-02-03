from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "password2")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    username_or_email = serializers.CharField(required=True)

    def validate_username_or_email(self, value):
        """Check if username or email exists and store user in context"""
        value = value.strip()
        user = None
        
        # Try to find by username first
        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            pass
        
        # If not found, try email
        if not user:
            try:
                user = User.objects.get(email=value)
            except User.DoesNotExist:
                pass
        
        if not user:
            raise serializers.ValidationError("No account found with this username or email.")
        
        # Store user in serializer context for later use
        self.user = user
        return value


class ResetPasswordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    password2 = serializers.CharField(write_only=True, min_length=8, required=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        validate_password(attrs["password"])
        return attrs

    def validate_user_id(self, value):
        """Check if user exists"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid user.")
        return value

    def save(self):
        user_id = self.validated_data["user_id"]
        password = self.validated_data["password"]
        user = User.objects.get(id=user_id)
        user.set_password(password)
        user.save()
        return user


