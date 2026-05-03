"""
File responsibility: Validates request data and converts Django models into JSON API responses.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from rest_framework import serializers

from apps.logistics.models import Shipment
from apps.orders.serializers import ORDER_STATUS_SLUGS


SHIPMENT_STATUS_SLUGS = {
    Shipment.Status.PENDING: "pending",
    Shipment.Status.ACCEPTED: "accepted",
    Shipment.Status.DECLINED: "declined",
    Shipment.Status.PICKED_UP: "picked up",
    Shipment.Status.IN_TRANSIT: "in transit",
    Shipment.Status.DELIVERED: "delivered",
}

SHIPMENT_STATUS_CODES = {value: key for key, value in SHIPMENT_STATUS_SLUGS.items()}


class MissionSerializer(serializers.ModelSerializer):
    """Defines MissionSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    id = serializers.SerializerMethodField(read_only=True)
    tracking_number = serializers.CharField(read_only=True)
    order_id = serializers.CharField(source="order.id", read_only=True)
    order_date = serializers.DateTimeField(source="order.order_date", read_only=True)
    delivery_request_date = serializers.SerializerMethodField(read_only=True)
    pickup_location = serializers.SerializerMethodField(read_only=True)
    delivery_location = serializers.SerializerMethodField(read_only=True)
    pickup_address = serializers.CharField(source="order.pickup_address", read_only=True)
    delivery_address = serializers.CharField(source="order.delivery_address", read_only=True)
    deadline = serializers.SerializerMethodField(read_only=True)
    shipping_fee = serializers.IntegerField(read_only=True)
    total_amount = serializers.IntegerField(source="order.total_amount", read_only=True)
    completed_at = serializers.SerializerMethodField(read_only=True)
    buyer_name = serializers.SerializerMethodField(read_only=True)
    farmer_name = serializers.SerializerMethodField(read_only=True)
    buyer_contact = serializers.CharField(source="order.buyer.person.phone_number", read_only=True)
    farmer_contact = serializers.CharField(source="order.farmer.person.phone_number", read_only=True)
    status = serializers.SerializerMethodField(read_only=True)
    order_status = serializers.SerializerMethodField(read_only=True)
    payment_method = serializers.SerializerMethodField(read_only=True)
    load_kg = serializers.SerializerMethodField(read_only=True)
    items = serializers.SerializerMethodField(read_only=True)
    pickup_wilaya_id = serializers.IntegerField(source="order.pickup_wilaya_id", read_only=True)
    pickup_wilaya_name = serializers.CharField(source="order.pickup_wilaya.name", read_only=True)
    pickup_commune_id = serializers.IntegerField(source="order.pickup_commune_id", read_only=True)
    pickup_commune_name = serializers.CharField(source="order.pickup_commune.name", read_only=True)
    delivery_wilaya_id = serializers.IntegerField(source="order.delivery_wilaya_id", read_only=True)
    delivery_wilaya_name = serializers.CharField(source="order.delivery_wilaya.name", read_only=True)
    delivery_commune_id = serializers.IntegerField(source="order.delivery_commune_id", read_only=True)
    delivery_commune_name = serializers.CharField(source="order.delivery_commune.name", read_only=True)

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Shipment
        fields = [
            "id",
            "tracking_number",
            "order_id",
            "order_date",
            "delivery_request_date",
            "pickup_location",
            "delivery_location",
            "pickup_address",
            "delivery_address",
            "pickup_wilaya_id",
            "pickup_wilaya_name",
            "pickup_commune_id",
            "pickup_commune_name",
            "delivery_wilaya_id",
            "delivery_wilaya_name",
            "delivery_commune_id",
            "delivery_commune_name",
            "deadline",
            "shipping_fee",
            "total_amount",
            "load_kg",
            "items",
            "completed_at",
            "buyer_name",
            "farmer_name",
            "buyer_contact",
            "farmer_contact",
            "status",
            "order_status",
            "payment_method",
        ]

    def get_id(self, obj):
        """Returns the stable database shipment ID used by transporter API actions."""
        return obj.id

    def get_deadline(self, obj):
        """Handles get_deadline, using the declared parameters and returning the expected value or API response."""
        if obj.estimated_delivery_date:
            return obj.estimated_delivery_date.date()
        return None

    def get_delivery_request_date(self, obj):
        """Returns when this delivery request was created from the existing shipment timestamp."""
        if obj.pickup_date:
            return obj.pickup_date
        return obj.order.order_date

    def get_completed_at(self, obj):
        """Handles get_completed_at, using the declared parameters and returning the expected value or API response."""
        if obj.actual_delivery_date:
            return obj.actual_delivery_date.date()
        return None

    def get_pickup_location(self, obj):
        """Handles get_pickup_location, using the declared parameters and returning the expected value or API response."""
        if obj.order.pickup_commune and obj.order.pickup_wilaya:
            return f"{obj.order.pickup_commune.name}, {obj.order.pickup_wilaya.name}"
        return obj.order.pickup_address

    def get_delivery_location(self, obj):
        """Handles get_delivery_location, using the declared parameters and returning the expected value or API response."""
        if obj.order.delivery_commune and obj.order.delivery_wilaya:
            return f"{obj.order.delivery_commune.name}, {obj.order.delivery_wilaya.name}"
        return obj.order.delivery_address

    def get_load_kg(self, obj):
        """Handles get_load_kg, using the declared parameters and returning the expected value or API response."""
        return sum(item.quantity for item in obj.order.items.all())

    def get_status(self, obj):
        """Handles get_status, using the declared parameters and returning the expected value or API response."""
        return SHIPMENT_STATUS_SLUGS.get(obj.status, "pending")

    def get_order_status(self, obj):
        """Returns the buyer/farmer order status alongside the transporter shipment status."""
        return ORDER_STATUS_SLUGS.get(obj.order.status, "pending")

    def get_payment_method(self, obj):
        """Returns the stored payment method when the checkout payment exists."""
        payment = obj.order.payments.order_by("id").first()
        return payment.payment_method if payment else ""

    def get_buyer_name(self, obj):
        """Returns the buyer display name from the linked user account."""
        person = obj.order.buyer.person
        full_name = f"{person.first_name} {person.last_name}".strip()
        return full_name or person.email

    def get_farmer_name(self, obj):
        """Returns the farmer display name from the linked user account."""
        person = obj.order.farmer.person
        full_name = f"{person.first_name} {person.last_name}".strip()
        return full_name or person.email

    def get_items(self, obj):
        """Summarizes real order items so transporters know exactly what they are carrying."""
        return [
            {
                "name": item.product_list.product.name,
                "quantity": item.quantity,
                "unit": item.product_list.product.unit,
                "unit_price": item.price,
                "total": item.total_items_price,
            }
            for item in obj.order.items.all()
        ]


class MissionStatusSerializer(serializers.Serializer):
    """Defines MissionStatusSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    status = serializers.ChoiceField(choices=sorted(SHIPMENT_STATUS_CODES.keys()))

    def get_status_code(self):
        """Handles get_status_code, using the declared parameters and returning the expected value or API response."""
        return SHIPMENT_STATUS_CODES[self.validated_data["status"]]
