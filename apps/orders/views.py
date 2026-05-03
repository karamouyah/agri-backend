"""
File responsibility: Processes HTTP API requests, checks permissions, queries models, and returns REST responses.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsBuyer
from apps.common.permissions import IsMinistry
from apps.orders.models import Order, Payment
from apps.orders.serializers import (
    AdminOrderSerializer,
    CheckoutSerializer,
    InvoiceSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
)
from apps.users.models import User


class CheckoutView(generics.CreateAPIView):
    """Defines CheckoutView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = CheckoutSerializer
    permission_classes = [IsBuyer]

    def create(self, request, *args, **kwargs):
        """Handles create, using the declared parameters and returning the expected value or API response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class MyOrdersView(generics.ListAPIView):
    """Defines MyOrdersView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        user = self.request.user
        base = Order.objects.select_related(
            "delivery_wilaya",
            "delivery_commune",
            "pickup_wilaya",
            "pickup_commune",
        ).prefetch_related("items", "items__product_list", "payments", "shipments")

        if user.role == User.Role.BUYER and hasattr(user, "buyer"):
            return base.filter(buyer=user.buyer)
        if user.role == User.Role.FARMER and hasattr(user, "farmer"):
            return base.filter(farmer=user.farmer)
        return Order.objects.none()


class AdminOrdersView(generics.ListAPIView):
    """Read-only Ministry/Admin order and transaction tracking list."""
    serializer_class = AdminOrderSerializer
    permission_classes = [IsMinistry]

    def get_queryset(self):
        """Returns all orders with the related data needed by the admin order table."""
        return Order.objects.select_related(
            "buyer",
            "buyer__person",
            "farmer",
            "farmer__person",
            "delivery_wilaya",
            "delivery_commune",
            "pickup_wilaya",
            "pickup_commune",
        ).prefetch_related(
            "items",
            "items__product_list",
            "items__product_list__product",
            "items__product_list__product__category",
            "payments",
            "shipments",
            "shipments__transporter",
            "shipments__transporter__person",
        )


class UpdateOrderStatusView(APIView):
    """Defines UpdateOrderStatusView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, public_id):
        """Handles patch, using the declared parameters and returning the expected value or API response."""
        order = Order.objects.filter(id=public_id).first()
        if not order:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        allowed = {User.Role.FARMER, User.Role.TRANSPORTER, User.Role.MINISTRY}
        if user.role not in allowed:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.status = serializer.get_status_code()
        order.save(update_fields=["status"])

        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)


class MyInvoicesView(generics.ListAPIView):
    """Defines MyInvoicesView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        user = self.request.user
        base = Payment.objects.select_related("order")
        if user.role == User.Role.BUYER and hasattr(user, "buyer"):
            return base.filter(order__buyer=user.buyer)
        if user.role == User.Role.FARMER and hasattr(user, "farmer"):
            return base.filter(order__farmer=user.farmer)
        return Payment.objects.none()
