from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r"^\+?[0-9 ()-]{7,20}$",
    message="Enter a valid phone number (7-20 digits, may start with +).",
)