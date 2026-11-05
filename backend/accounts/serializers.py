from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from candidates.models import Candidate
from recruiters.models import Recruiter

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Safe public view of a user. Email and role cannot be changed here."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "date_joined"]
        read_only_fields = ["id", "email", "role", "date_joined"]


class UserUpdateSerializer(serializers.ModelSerializer):
    """Used only for PATCH /api/auth/me/. Only first_name and last_name are writable;
    submitting any protected field is rejected with a 400."""

    PROTECTED_FIELDS = (
        "id", "email", "role", "username", "password",
        "date_joined", "is_active", "is_staff", "is_superuser",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name"]

    def to_internal_value(self, data):
        blocked = [name for name in self.PROTECTED_FIELDS if name in data]
        if blocked:
            raise serializers.ValidationError(
                {name: ["This field cannot be changed."] for name in blocked}
            )
        return super().to_internal_value(data)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "password", "password2"]
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
        }

    def validate_email(self, value):
        email = value.strip().lower()
        if (
            User.objects.filter(email__iexact=email).exists()
            or User.objects.filter(username__iexact=email).exists()
        ):
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords do not match."})

        # Run Django's password validators (length, common, numeric, similarity)
        temp_user = User(
            username=attrs["email"],
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=temp_user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        # 'role' arrives from the view via serializer.save(role=...)
        validated_data.pop("password2")
        password = validated_data.pop("password")
        with transaction.atomic():  # user and profile are saved together or not at all
            user = User(username=validated_data["email"], **validated_data)
            user.set_password(password)  # hashes the password (PBKDF2)
            user.save()
            if user.role == User.Role.RECRUITER:
                Recruiter.objects.create(user=user)
            else:
                Candidate.objects.create(user=user)
        return user


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login with email + password. Adds the role to the token and response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop(self.username_field, None)
        self.fields["email"] = serializers.EmailField(write_only=True)

    def validate(self, attrs):
        # username was stored as the lower-cased email at registration
        attrs[self.username_field] = attrs.pop("email").strip().lower()
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data