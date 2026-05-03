"""
File responsibility: Exposes the Django WSGI application for traditional deployment servers.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agri_backend.settings")

application = get_wsgi_application()
