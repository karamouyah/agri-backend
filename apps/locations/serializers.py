"""
File responsibility: Validates request data and converts Django models into JSON API responses.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from rest_framework import serializers

from apps.locations.models import Commune, Wilaya


class CommuneSerializer(serializers.ModelSerializer):
    """Defines CommuneSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Commune
        fields = ["id", "name", "wilaya"]


class WilayaSerializer(serializers.ModelSerializer):
    """Defines WilayaSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Wilaya
        fields = ["id", "code", "name"]


class WilayaTreeSerializer(serializers.ModelSerializer):
    """Defines WilayaTreeSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    communes = CommuneSerializer(many=True, read_only=True)

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Wilaya
        fields = ["id", "code", "name", "communes"]


class LocationValidationSerializer(serializers.Serializer):
    """Defines LocationValidationSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    wilaya_id = serializers.IntegerField()
    commune_id = serializers.IntegerField()

    def validate(self, attrs):
        """Handles validate, using the declared parameters and returning the expected value or API response."""
        wilaya = Wilaya.objects.filter(id=attrs["wilaya_id"]).first()
        commune = Commune.objects.filter(id=attrs["commune_id"]).first()

        if not wilaya:
            raise serializers.ValidationError({"wilaya_id": "Selected wilaya does not exist."})
        if not commune:
            raise serializers.ValidationError({"commune_id": "Selected commune does not exist."})
        if commune.wilaya_id != wilaya.id:
            raise serializers.ValidationError({"commune_id": "Selected commune does not belong to the wilaya."})

        attrs["wilaya"] = wilaya
        attrs["commune"] = commune
        return attrs

