"""
File responsibility: Implements a custom Django management command for loading project data.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.core.management.base import BaseCommand

from apps.locations.data import sync_algeria_locations


class Command(BaseCommand):
    """Defines Command for this app and is used by the serializers, views, routes, or admin when imported."""
    help = "Seed the official Algeria wilayas and communes dataset."

    def handle(self, *args, **options):
        """Handles handle, using the declared parameters and returning the expected value or API response."""
        summary = sync_algeria_locations()
        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Algeria locations: "
                f"{summary['wilayas']} wilayas and {summary['communes']} communes."
            )
        )

