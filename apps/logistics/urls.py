"""
File responsibility: Maps app-level API paths to the views and viewsets in this Django app.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.urls import path

from apps.logistics.views import (
    AcceptMissionView,
    ActiveDeliveriesView,
    CompletedDeliveriesView,
    DeclineMissionView,
    DeclinedDeliveriesView,
    DeliveryByIdView,
    DeliveryRequestsView,
    UpdateDeliveryStatusView,
)

urlpatterns = [
    path("requests/", DeliveryRequestsView.as_view(), name="delivery-requests"),
    path("active/", ActiveDeliveriesView.as_view(), name="active-deliveries"),
    path("completed/", CompletedDeliveriesView.as_view(), name="completed-deliveries"),
    path("declined/", DeclinedDeliveriesView.as_view(), name="declined-deliveries"),
    path("missions/<str:mission_id>/", DeliveryByIdView.as_view(), name="delivery-by-id"),
    path("missions/<str:mission_id>/accept/", AcceptMissionView.as_view(), name="accept-mission"),
    path("missions/<str:mission_id>/decline/", DeclineMissionView.as_view(), name="decline-mission"),
    path("missions/<str:mission_id>/status/", UpdateDeliveryStatusView.as_view(), name="mission-status"),
]
