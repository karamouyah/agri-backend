"""
File responsibility: Implements a custom Django management command for loading project data.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.core.management.base import BaseCommand

from apps.catalog.catalog_data import sync_controlled_catalog
from apps.catalog.models import Category, Product


class Command(BaseCommand):
    """Defines Command for this app and is used by the serializers, views, routes, or admin when imported."""
    help = "Seed the controlled product catalog used by farmers."

    def handle(self, *args, **options):
        """Handles handle, using the declared parameters and returning the expected value or API response."""
        catalog = sync_controlled_catalog(Category, Product)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(catalog)} approved catalog products."))
