"""
File responsibility: Registers Django models or admin URLs so staff can manage backend data.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.contrib import admin

from apps.locations.models import Commune, Wilaya


@admin.register(Wilaya)
class WilayaAdmin(admin.ModelAdmin):
    """Defines WilayaAdmin for this app and is used by the serializers, views, routes, or admin when imported."""
    list_display = ["id", "code", "name"]
    search_fields = ["name", "code"]


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    """Defines CommuneAdmin for this app and is used by the serializers, views, routes, or admin when imported."""
    list_display = ["id", "name", "wilaya"]
    list_filter = ["wilaya"]
    search_fields = ["name", "wilaya__name"]

