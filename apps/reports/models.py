from django.conf import settings
from django.db import models


class Report(models.Model):
    """Text-only user report/signalement linked to optional marketplace records."""

    class Category(models.TextChoices):
        USER = "user", "User"
        ORDER = "order", "Order"
        PRODUCT = "product", "Product or listing"
        SHIPMENT = "shipment", "Delivery or shipment"
        PAYMENT = "payment", "Payment or transaction"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEWING = "reviewing", "Reviewing"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_reports",
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports_about_user",
    )
    related_order = models.ForeignKey(
        "orders.Order",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )
    related_product_listing = models.ForeignKey(
        "catalog.ProductList",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )
    related_shipment = models.ForeignKey(
        "logistics.Shipment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )
    related_payment = models.ForeignKey(
        "orders.Payment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )
    category = models.CharField(max_length=30, choices=Category.choices, blank=True)
    reason = models.CharField(max_length=160)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status"], name="report_status_idx"),
            models.Index(fields=["created_at"], name="report_created_idx"),
        ]

    def __str__(self):
        return f"Report<{self.id}:{self.status}>"
