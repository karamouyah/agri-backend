"""
File responsibility: Defines reusable role-based permission checks for Django REST Framework views.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from rest_framework.permissions import BasePermission


class IsRole(BasePermission):
    """Defines IsRole for this app and is used by the serializers, views, routes, or admin when imported."""
    allowed_roles = set()

    def has_permission(self, request, view):
        """Handles has_permission, using the declared parameters and returning the expected value or API response."""
        user = request.user
        if not (user and user.is_authenticated):
            return False

        role_value = getattr(user, "role_slug", None)
        if not role_value:
            raw_role = getattr(user, "role", None)
            role_value = str(raw_role).lower() if raw_role is not None else ""

        return role_value in self.allowed_roles


class IsMinistry(IsRole):
    """Defines IsMinistry for this app and is used by the serializers, views, routes, or admin when imported."""
    allowed_roles = {"ministry"}


class IsFarmer(IsRole):
    """Defines IsFarmer for this app and is used by the serializers, views, routes, or admin when imported."""
    allowed_roles = {"farmer"}


class IsBuyer(IsRole):
    """Defines IsBuyer for this app and is used by the serializers, views, routes, or admin when imported."""
    allowed_roles = {"buyer"}


class IsTransporter(IsRole):
    """Defines IsTransporter for this app and is used by the serializers, views, routes, or admin when imported."""
    allowed_roles = {"transporter"}
