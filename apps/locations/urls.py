"""
File responsibility: Maps app-level API paths to the views and viewsets in this Django app.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.urls import path

from apps.locations.views import CommuneListView, ValidateLocationView, WilayaListView, WilayaTreeView

urlpatterns = [
    path("wilayas/", WilayaListView.as_view(), name="location-wilayas"),
    path("communes/", CommuneListView.as_view(), name="location-communes"),
    path("tree/", WilayaTreeView.as_view(), name="location-tree"),
    path("validate/", ValidateLocationView.as_view(), name="location-validate"),
]

