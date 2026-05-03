"""
File responsibility: Connects the Django project URL paths to each backend app API router.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Defines HealthView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        """Handles get, using the declared parameters and returning the expected value or API response."""
        return Response({"status": "ok"})


class ApiRootView(APIView):
    """Defines ApiRootView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        """Handles get, using the declared parameters and returning the expected value or API response."""
        return Response(
            {
                "message": "Agri API is running.",
                "health": "/api/health/",
                "auth": "/api/auth/",
                "products": "/api/products/",
                "locations": "/api/locations/",
                "catalog": "/api/catalog/",
                "orders": "/api/orders/",
                "logistics": "/api/logistics/",
                "reports": "/api/reports/",
                "documents": "/api/documents/",
            }
        )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", ApiRootView.as_view(), name="api-root"),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/auth/", include("apps.users.urls")),
    path("api/products/", include("apps.catalog.admin_product_urls")),
    path("api/locations/", include("apps.locations.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/logistics/", include("apps.logistics.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/documents/", include("apps.documents.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
