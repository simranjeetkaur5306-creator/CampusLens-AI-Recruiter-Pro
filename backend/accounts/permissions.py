from rest_framework.permissions import BasePermission

from .models import User


class IsCandidate(BasePermission):
    message = "Only candidates can access this resource."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.Role.CANDIDATE)


class IsRecruiter(BasePermission):
    message = "Only recruiters can access this resource."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.Role.RECRUITER)