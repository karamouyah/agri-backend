"""
File responsibility: Processes HTTP API requests, checks permissions, queries models, and returns REST responses.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsTransporter
from apps.logistics.models import Shipment
from apps.logistics.serializers import MissionSerializer, MissionStatusSerializer
from apps.orders.models import Order
from apps.users.models import Transporter


def mission_queryset():
    """Handles mission_queryset, using the declared parameters and returning the expected value or API response."""
    return Shipment.objects.select_related(
        "order",
        "order__buyer__person",
        "order__farmer__person",
        "order__pickup_wilaya",
        "order__pickup_commune",
        "order__delivery_wilaya",
        "order__delivery_commune",
        "transporter",
        "transporter__person",
    ).prefetch_related("order__items__product_list__product", "order__payments")


def eligible_shipments_for_transporter(transporter):
    """Handles eligible_shipments_for_transporter, using the declared parameters and returning the expected value or API response."""
    if not transporter or not transporter.max_load_kg:
        return Shipment.objects.none()

    delivery_wilaya_ids = list(transporter.delivery_wilayas.values_list("id", flat=True))
    if not delivery_wilaya_ids:
        return Shipment.objects.none()

    return (
        mission_queryset()
        .filter(status=Shipment.Status.PENDING, order__delivery_wilaya_id__in=delivery_wilaya_ids)
        .annotate(load_kg=Sum("order__items__quantity"))
        .filter(load_kg__lte=transporter.max_load_kg)
    )


def mission_filter_for_identifier(mission_id):
    """Allows existing tracking-number URLs and new stable database IDs to resolve missions."""
    lookup = {"tracking_number": mission_id}
    try:
        lookup = {"id": int(mission_id)}
    except (TypeError, ValueError):
        pass
    return lookup


class DeliveryRequestsView(generics.ListAPIView):
    """Defines DeliveryRequestsView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = MissionSerializer
    permission_classes = [IsTransporter]

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        return eligible_shipments_for_transporter(getattr(self.request.user, "transporter", None))


class ActiveDeliveriesView(generics.ListAPIView):
    """Defines ActiveDeliveriesView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = MissionSerializer
    permission_classes = [IsTransporter]

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        transporter = getattr(self.request.user, "transporter", None)
        if not transporter:
            return Shipment.objects.none()

        return mission_queryset().filter(
            transporter=transporter,
            status__in=[Shipment.Status.ACCEPTED, Shipment.Status.PICKED_UP, Shipment.Status.IN_TRANSIT],
        )


class CompletedDeliveriesView(generics.ListAPIView):
    """Defines CompletedDeliveriesView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = MissionSerializer
    permission_classes = [IsTransporter]

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        transporter = getattr(self.request.user, "transporter", None)
        if not transporter:
            return Shipment.objects.none()

        return mission_queryset().filter(
            transporter=transporter,
            status=Shipment.Status.DELIVERED,
        ).order_by("-actual_delivery_date", "-id")


class DeclinedDeliveriesView(generics.ListAPIView):
    """Lists missions this transporter declined or that were cancelled after assignment."""
    serializer_class = MissionSerializer
    permission_classes = [IsTransporter]

    def get_queryset(self):
        """Returns declined shipments only when they belong to the signed-in transporter."""
        transporter = getattr(self.request.user, "transporter", None)
        if not transporter:
            return Shipment.objects.none()

        return mission_queryset().filter(
            transporter=transporter,
            status=Shipment.Status.DECLINED,
        ).order_by("-id")


class DeliveryByIdView(generics.RetrieveAPIView):
    """Defines DeliveryByIdView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = MissionSerializer
    permission_classes = [IsTransporter]
    lookup_url_kwarg = "mission_id"
    queryset = mission_queryset()

    def get_object(self):
        """Resolves a mission by database ID while preserving tracking-number compatibility."""
        queryset = self.filter_queryset(self.get_queryset())
        mission_id = self.kwargs[self.lookup_url_kwarg]
        obj = get_object_or_404(queryset, **mission_filter_for_identifier(mission_id))
        self.check_object_permissions(self.request, obj)
        return obj


class AcceptMissionView(APIView):
    """Defines AcceptMissionView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsTransporter]

    def post(self, request, mission_id):
        """Handles post, using the declared parameters and returning the expected value or API response."""
        shipment = mission_queryset().filter(**mission_filter_for_identifier(mission_id)).first()
        if not shipment:
            return Response({"detail": "Mission not found."}, status=status.HTTP_404_NOT_FOUND)

        transporter = getattr(request.user, "transporter", None)
        if not transporter:
            transporter = Transporter.objects.create(person=request.user)

        if shipment.status != Shipment.Status.PENDING:
            return Response({"detail": "This mission is no longer available."}, status=status.HTTP_400_BAD_REQUEST)

        if not eligible_shipments_for_transporter(transporter).filter(id=shipment.id).exists():
            return Response(
                {
                    "detail": (
                        "This mission is outside your delivery wilayas or exceeds your maximum load capacity."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        shipment.transporter = transporter
        shipment.status = Shipment.Status.ACCEPTED
        shipment.save(update_fields=["transporter", "status"])
        return Response(MissionSerializer(shipment).data)


class DeclineMissionView(APIView):
    """Defines DeclineMissionView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsTransporter]

    def post(self, request, mission_id):
        """Handles post, using the declared parameters and returning the expected value or API response."""
        shipment = mission_queryset().filter(**mission_filter_for_identifier(mission_id)).first()
        if not shipment:
            return Response({"detail": "Mission not found."}, status=status.HTTP_404_NOT_FOUND)

        transporter = getattr(request.user, "transporter", None)
        if not transporter:
            transporter = Transporter.objects.create(person=request.user)

        shipment.transporter = transporter
        shipment.status = Shipment.Status.DECLINED
        shipment.save(update_fields=["transporter", "status"])
        return Response(MissionSerializer(shipment).data)


class UpdateDeliveryStatusView(APIView):
    """Defines UpdateDeliveryStatusView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsTransporter]

    def patch(self, request, mission_id):
        """Handles patch, using the declared parameters and returning the expected value or API response."""
        transporter = getattr(request.user, "transporter", None)
        if not transporter:
            return Response({"detail": "Mission not found."}, status=status.HTTP_404_NOT_FOUND)

        shipment = mission_queryset().filter(
            **mission_filter_for_identifier(mission_id),
            transporter=transporter,
        ).first()
        if not shipment:
            return Response({"detail": "Mission not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MissionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        shipment.status = serializer.get_status_code()
        update_fields = ["status"]

        # Keep order tracking aligned with transporter progress without changing checkout or farmer workflows.
        if shipment.status == Shipment.Status.PICKED_UP:
            shipment.order.status = Order.Status.SHIPPED
            shipment.order.save(update_fields=["status"])
        elif shipment.status == Shipment.Status.IN_TRANSIT:
            shipment.order.status = Order.Status.IN_TRANSIT
            shipment.order.save(update_fields=["status"])
        elif shipment.status == Shipment.Status.DELIVERED:
            shipment.order.status = Order.Status.DELIVERED
            shipment.actual_delivery_date = timezone.now()
            update_fields.append("actual_delivery_date")
            shipment.order.save(update_fields=["status"])

        shipment.save(update_fields=update_fields)
        return Response(MissionSerializer(shipment).data)
