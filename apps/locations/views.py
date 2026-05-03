"""
File responsibility: Processes HTTP API requests, checks permissions, queries models, and returns REST responses.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.locations.models import Commune, Wilaya
from apps.locations.serializers import (
    CommuneSerializer,
    LocationValidationSerializer,
    WilayaSerializer,
    WilayaTreeSerializer,
)


class WilayaListView(ListAPIView):
    """Defines WilayaListView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = WilayaSerializer
    queryset = Wilaya.objects.all().order_by("id")


class CommuneListView(ListAPIView):
    """Defines CommuneListView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = CommuneSerializer

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        queryset = Commune.objects.select_related("wilaya").all().order_by("name")
        wilaya_id = self.request.query_params.get("wilaya")
        if wilaya_id:
            queryset = queryset.filter(wilaya_id=wilaya_id)
        return queryset


class WilayaTreeView(ListAPIView):
    """Defines WilayaTreeView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = WilayaTreeSerializer
    queryset = Wilaya.objects.prefetch_related("communes").all().order_by("id")


class ValidateLocationView(APIView):
    """Defines ValidateLocationView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Handles post, using the declared parameters and returning the expected value or API response."""
        serializer = LocationValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wilaya = serializer.validated_data["wilaya"]
        commune = serializer.validated_data["commune"]
        return Response(
            {
                "valid": True,
                "wilaya": {"id": wilaya.id, "code": wilaya.code, "name": wilaya.name},
                "commune": {"id": commune.id, "name": commune.name},
            }
        )

