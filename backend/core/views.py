from django.db import connection
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request):
    """Public endpoint: confirms the API, PostgreSQL and pgvector are working."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            row = cursor.fetchone()
    except Exception:
        # Do not leak internal error details to the client
        return Response({"status": "error", "database": "unreachable"}, status=503)

    return Response(
        {
            "status": "ok",
            "database": "connected",
            "pgvector": row[0] if row else "not installed",
        }
    )