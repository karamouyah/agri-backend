"""
File responsibility: Maps app-level API paths to the views and viewsets in this Django app.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.users.views import (
    AdminUserViewSet,
    BuyerProfileView,
    CurrentUserView,
    FarmProfileView,
    GenerateReportView,
    LoginView,
    NationalStatsView,
    RefreshView,
    RegisterView,
    TransporterProfileView,
)

router = DefaultRouter()
router.register("admin/users", AdminUserViewSet, basename="admin-users")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="token-refresh"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("farmer/profile/", FarmProfileView.as_view(), name="farmer-profile"),
    path("buyer/profile/", BuyerProfileView.as_view(), name="buyer-profile"),
    path("transporter/profile/", TransporterProfileView.as_view(), name="transporter-profile"),
    path("admin/stats/", NationalStatsView.as_view(), name="national-stats"),
    path("admin/reports/", GenerateReportView.as_view(), name="generate-report"),
    path("", include(router.urls)),
]
