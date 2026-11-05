from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .permissions import IsCandidate, IsRecruiter
from .serializers import (
    EmailTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


class CandidateRegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    role = User.Role.CANDIDATE

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(role=self.role)  # role is set by the server
        return Response(
            {"message": "Registration successful.", "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class RecruiterRegisterView(CandidateRegisterView):
    role = User.Role.RECRUITER


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class LogoutView(APIView):
    """Blacklists the refresh token so it can no longer be used."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"message": "Refresh token is required.", "errors": {"refresh": ["This field is required."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response(
                {"message": "Invalid or expired refresh token.", "errors": None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Logged out successfully."})


class MeView(generics.RetrieveUpdateAPIView):
    """GET or PATCH the logged-in user's own profile."""

    serializer_class = UserSerializer  # used for GET
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(
            self.get_object(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)  # full profile in the response

# ---- TEMPORARY: proves role-based access works. Remove in Phase 4. ----
class CandidateOnlyCheckView(APIView):
    permission_classes = [IsAuthenticated, IsCandidate]

    def get(self, request):
        return Response({"message": "Access granted: you are a candidate."})


class RecruiterOnlyCheckView(APIView):
    permission_classes = [IsAuthenticated, IsRecruiter]

    def get(self, request):
        return Response({"message": "Access granted: you are a recruiter."})