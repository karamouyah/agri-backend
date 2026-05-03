"""
File responsibility: Defines database tables and relationships for this Django app.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.db import models

from apps.orders.models import Order, OrderItem
from apps.users.models import Buyer, Transporter


class Shipment(models.Model):
    """Defines Shipment for this app and is used by the serializers, views, routes, or admin when imported."""
    class Status(models.IntegerChoices):
        """Defines Status for this app and is used by the serializers, views, routes, or admin when imported."""
        PENDING = 0, "Pending"
        ACCEPTED = 1, "Accepted"
        DECLINED = 2, "Declined"
        PICKED_UP = 3, "Picked Up"
        IN_TRANSIT = 4, "In Transit"
        DELIVERED = 5, "Delivered"

    id = models.AutoField(primary_key=True, db_column="IDShipping")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column="IDOrder", related_name="shipments")
    transporter = models.ForeignKey(
        Transporter,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="IDTransporter",
        related_name="shipments",
    )
    tracking_number = models.CharField(max_length=100, blank=True, db_column="TrackingNumber")
    status = models.PositiveSmallIntegerField(choices=Status.choices, default=Status.PENDING, db_column="Status")
    shipping_fee = models.IntegerField(default=0, db_column="ShippingFee")
    pickup_date = models.DateTimeField(null=True, blank=True, db_column="PickupDate")
    estimated_delivery_date = models.DateTimeField(null=True, blank=True, db_column="EstimatedDeliveryDate")
    actual_delivery_date = models.DateTimeField(null=True, blank=True, db_column="ActualDeliveryDate")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Shipment"
        ordering = ["-pickup_date", "-id"]

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return self.tracking_number or f"SHIP-{self.id}"


class TransporterReview(models.Model):
    """Defines TransporterReview for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDReview")
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE, db_column="IDBuyer", related_name="transporter_reviews")
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        db_column="IDShipping",
        related_name="reviews",
    )
    rating = models.IntegerField(db_column="Rating")
    review_text = models.CharField(max_length=255, blank=True, db_column="ReviewText")
    review_date = models.DateTimeField(auto_now_add=True, db_column="ReviewDate")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "TransporterReview"


class ItemReview(models.Model):
    """Defines ItemReview for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDItemReview")
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        db_column="IDOrderItem",
        related_name="item_reviews",
    )
    rating = models.IntegerField(db_column="Rating")
    review_text = models.CharField(max_length=255, blank=True, db_column="ReviewText")
    review_date = models.DateTimeField(auto_now_add=True, db_column="ReviewDate")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "ItemReview"
