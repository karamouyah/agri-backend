"""
File responsibility: Declares the Django app configuration used by INSTALLED_APPS.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    """Defines OrdersConfig for this app and is used by the serializers, views, routes, or admin when imported."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
