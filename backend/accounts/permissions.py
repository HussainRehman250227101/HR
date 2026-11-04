"""Reusable role-based API permissions."""

from rest_framework.permissions import BasePermission

from .models import UserRole


class IsHRAdmin(BasePermission):
    message = "HR Administrator role is required."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or request.user.role == UserRole.ADMIN)
        )


class IsRecruiterOrAdmin(BasePermission):
    message = "HR Recruiter or HR Administrator role is required."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role in (UserRole.ADMIN, UserRole.RECRUITER)
            )
        )


class IsHiringManagerOrAdmin(BasePermission):
    message = "Hiring Manager or HR Administrator role is required."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.role in (UserRole.ADMIN, UserRole.HIRING_MANAGER)
            )
        )
