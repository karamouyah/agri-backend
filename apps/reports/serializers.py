from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import ProductList
from apps.logistics.models import Shipment
from apps.orders.models import Order, Payment
from apps.reports.models import Report
from apps.users.models import User


def user_summary(user):
    if not user:
        return None
    full_name = f"{user.first_name} {user.last_name}".strip()
    return {
        "id": user.id,
        "name": full_name or user.email,
        "email": user.email,
        "role": user.role_slug,
    }


class ReportSerializer(serializers.ModelSerializer):
    reporter = serializers.SerializerMethodField()
    reported_user = serializers.SerializerMethodField()
    related_order = serializers.SerializerMethodField()
    related_product_listing = serializers.SerializerMethodField()
    related_shipment = serializers.SerializerMethodField()
    related_payment = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "reporter",
            "reported_user",
            "related_order",
            "related_product_listing",
            "related_shipment",
            "related_payment",
            "category",
            "reason",
            "description",
            "status",
            "admin_notes",
            "created_at",
            "updated_at",
        ]

    def get_reporter(self, obj):
        return user_summary(obj.reporter)

    def get_reported_user(self, obj):
        return user_summary(obj.reported_user)

    def get_related_order(self, obj):
        order = obj.related_order
        if not order:
            return None
        return {
            "id": order.id,
            "status": order.get_status_display(),
            "total_amount": order.total_amount,
            "created_at": order.order_date,
        }

    def get_related_product_listing(self, obj):
        listing = obj.related_product_listing
        if not listing:
            return None
        product = getattr(listing, "product", None)
        farmer = getattr(listing, "farmer", None)
        farmer_person = getattr(farmer, "person", None)
        farmer_data = user_summary(farmer_person)
        return {
            "id": listing.id,
            "name": product.name if product else "",
            "price": listing.price,
            "quantity": listing.quantity,
            "farmer_name": farmer_data["name"] if farmer_data else "",
        }

    def get_related_shipment(self, obj):
        shipment = obj.related_shipment
        if not shipment:
            return None
        return {
            "id": shipment.id,
            "tracking_number": shipment.tracking_number or "",
            "status": shipment.get_status_display(),
        }

    def get_related_payment(self, obj):
        payment = obj.related_payment
        if not payment:
            return None
        return {
            "id": payment.id,
            "amount": payment.amount,
            "method": payment.payment_method,
            "transaction_date": payment.transaction_date,
        }


class ReportCreateSerializer(serializers.ModelSerializer):
    duplicate_window = timedelta(minutes=5)

    reported_user_id = serializers.PrimaryKeyRelatedField(
        source="reported_user",
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    related_order_id = serializers.PrimaryKeyRelatedField(
        source="related_order",
        queryset=Order.objects.all(),
        required=False,
        allow_null=True,
    )
    related_product_listing_id = serializers.PrimaryKeyRelatedField(
        source="related_product_listing",
        queryset=ProductList.objects.all(),
        required=False,
        allow_null=True,
    )
    related_shipment_id = serializers.PrimaryKeyRelatedField(
        source="related_shipment",
        queryset=Shipment.objects.all(),
        required=False,
        allow_null=True,
    )
    related_payment_id = serializers.PrimaryKeyRelatedField(
        source="related_payment",
        queryset=Payment.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Report
        fields = [
            "reported_user_id",
            "related_order_id",
            "related_product_listing_id",
            "related_shipment_id",
            "related_payment_id",
            "category",
            "reason",
            "description",
        ]
        extra_kwargs = {
            "category": {"required": False, "allow_blank": True},
            "reason": {"required": True, "allow_blank": False},
            "description": {"required": True, "allow_blank": False},
        }

    def validate(self, attrs):
        attrs["category"] = (attrs.get("category") or "").strip()
        attrs["reason"] = (attrs.get("reason") or "").strip()
        attrs["description"] = (attrs.get("description") or "").strip()

        if not attrs["reason"] or not attrs["description"]:
            raise serializers.ValidationError("Reason and description are required.")

        has_target = any(
            attrs.get(field)
            for field in (
                "reported_user",
                "related_order",
                "related_product_listing",
                "related_shipment",
                "related_payment",
            )
        )
        if not has_target and not attrs.get("category"):
            raise serializers.ValidationError("Select a report category or a related target.")

        reporter = self.context["request"].user
        duplicate_filter = {
            "reporter": reporter,
            "category": attrs.get("category", ""),
            "reason__iexact": attrs["reason"],
            "description__iexact": attrs["description"],
            "reported_user": attrs.get("reported_user"),
            "related_order": attrs.get("related_order"),
            "related_product_listing": attrs.get("related_product_listing"),
            "related_shipment": attrs.get("related_shipment"),
            "related_payment": attrs.get("related_payment"),
            "created_at__gte": timezone.now() - self.duplicate_window,
        }
        if Report.objects.filter(**duplicate_filter).exists():
            raise serializers.ValidationError("You already submitted this report recently.")
        return attrs

    def create(self, validated_data):
        return Report.objects.create(reporter=self.context["request"].user, **validated_data)


class AdminReportUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["status", "admin_notes"]
        extra_kwargs = {
            "status": {"required": False},
            "admin_notes": {"required": False, "allow_blank": True},
        }
