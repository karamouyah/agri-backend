from rest_framework import generics, status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsMinistry
from apps.reports.models import Report
from apps.reports.serializers import AdminReportUpdateSerializer, ReportCreateSerializer, ReportSerializer
from apps.users.models import User


class IsApprovedReporter(BasePermission):
    """Allows approved buyer, farmer, and transporter accounts to submit reports."""

    allowed_roles = {User.Role.BUYER, User.Role.FARMER, User.Role.TRANSPORTER}

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.status == User.Status.APPROVED
            and user.role in self.allowed_roles
        )


def report_queryset():
    return Report.objects.select_related(
        "reporter",
        "reported_user",
        "related_order",
        "related_product_listing",
        "related_product_listing__product",
        "related_product_listing__farmer",
        "related_product_listing__farmer__person",
        "related_shipment",
        "related_payment",
    )


class ReportCreateView(generics.CreateAPIView):
    serializer_class = ReportCreateSerializer
    permission_classes = [IsAuthenticated, IsApprovedReporter]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class MyReportsView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated, IsApprovedReporter]

    def get_queryset(self):
        return report_queryset().filter(reporter=self.request.user)


class AdminReportsView(generics.ListAPIView):
    serializer_class = ReportSerializer
    permission_classes = [IsMinistry]

    def get_queryset(self):
        return report_queryset()


class AdminReportDetailView(generics.UpdateAPIView):
    queryset = report_queryset()
    serializer_class = AdminReportUpdateSerializer
    permission_classes = [IsMinistry]
    http_method_names = ["patch", "options"]

    def patch(self, request, *args, **kwargs):
        allowed_fields = {"status", "admin_notes"}
        blocked_fields = set(request.data.keys()) - allowed_fields
        if blocked_fields:
            return Response(
                {"detail": "Only status and admin_notes can be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = super().patch(request, *args, **kwargs)
        report = self.get_object()
        return Response(ReportSerializer(report).data, status=response.status_code)
