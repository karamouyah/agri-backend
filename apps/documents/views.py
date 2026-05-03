from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsMinistry
from apps.documents.models import VerificationDocument
from apps.documents.serializers import (
    AdminVerificationDocumentUpdateSerializer,
    VerificationDocumentSerializer,
    VerificationDocumentUploadSerializer,
)
from apps.users.models import User


class IsBuyerOrTransporter(BasePermission):
    allowed_roles = {User.Role.BUYER, User.Role.TRANSPORTER, User.Role.FARMER}

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.allowed_roles)


def document_queryset():
    return VerificationDocument.objects.select_related("user").all()


class VerificationDocumentUploadView(generics.CreateAPIView):
    serializer_class = VerificationDocumentUploadSerializer
    permission_classes = [IsAuthenticated, IsBuyerOrTransporter]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(
            VerificationDocumentSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MyVerificationDocumentsView(generics.ListAPIView):
    serializer_class = VerificationDocumentSerializer
    permission_classes = [IsAuthenticated, IsBuyerOrTransporter]

    def get_queryset(self):
        return document_queryset().filter(user=self.request.user)


class AdminVerificationDocumentsView(generics.ListAPIView):
    serializer_class = VerificationDocumentSerializer
    permission_classes = [IsMinistry]

    def get_queryset(self):
        return document_queryset()


class AdminVerificationDocumentDetailView(generics.UpdateAPIView):
    queryset = document_queryset()
    serializer_class = AdminVerificationDocumentUpdateSerializer
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
        document = self.get_object()
        return Response(VerificationDocumentSerializer(document, context={"request": request}).data, status=response.status_code)

