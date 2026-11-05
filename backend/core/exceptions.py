from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Every API error becomes {"message": "...", "errors": ...}."""
    response = exception_handler(exc, context)
    if response is None:
        return None  # unexpected server errors keep Django's normal handling

    if isinstance(exc, ValidationError):
        message, errors = "Validation failed.", response.data
    else:
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        message, errors = str(detail or "Request failed."), None

    response.data = {"message": message, "errors": errors}
    return response