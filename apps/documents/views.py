from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.encoding import smart_str
from django.utils.text import get_valid_filename
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsMinistry
from apps.documents.converters import convert_document_to_pdf, PDFConversionError
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


def can_access_document(user, document):
    return bool(
        user
        and user.is_authenticated
        and (
            user == document.user
            or user.role == User.Role.MINISTRY
        )
    )


class VerificationDocumentUploadView(generics.CreateAPIView):
    serializer_class = VerificationDocumentUploadSerializer
    permission_classes = [IsAuthenticated, IsBuyerOrTransporter]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        
        # Attempt PDF conversion (non-blocking, errors logged but don't crash)
        try:
            file_obj = document.file.open('rb')
            content_type = document.file.content_type or ""
            original_filename = document.file.name
            
            pdf_bytes, pdf_filename = convert_document_to_pdf(
                file_obj,
                content_type,
                original_filename
            )
            
            if pdf_bytes and pdf_filename:
                from django.core.files.base import ContentFile
                document.pdf_file.save(
                    pdf_filename,
                    ContentFile(pdf_bytes),
                    save=True
                )
                
        except PDFConversionError as e:
            # Log conversion error but don't fail the upload
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"PDF conversion skipped for document {document.id}: {str(e)}")
        except Exception as e:
            # Catch any other errors to ensure upload doesn't fail
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error during PDF conversion for document {document.id}: {str(e)}")
        finally:
            if hasattr(file_obj, 'close'):
                file_obj.close()
        
        return Response(
            VerificationDocumentSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class VerificationDocumentDownloadView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        document = get_object_or_404(document_queryset(), pk=kwargs["pk"])
        if not can_access_document(request.user, document):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if not document.file:
            raise Http404("Document file is missing.")

        try:
            file_handle = document.file.open("rb")
        except FileNotFoundError as exc:
            raise Http404("Document file is missing from storage.") from exc

        response = FileResponse(file_handle, as_attachment=True)
        filename = document.file.name.rsplit("/", 1)[-1]
        response["Content-Disposition"] = f'attachment; filename="{get_valid_filename(smart_str(filename))}"'
        return response


class VerificationDocumentDownloadPDFView(generics.RetrieveAPIView):
    """Download the converted PDF version of a document."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        document = get_object_or_404(document_queryset(), pk=kwargs["pk"])
        if not can_access_document(request.user, document):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # If PDF exists, serve it; otherwise fall back to original
        file_to_serve = document.pdf_file if document.pdf_file else document.file
        
        if not file_to_serve:
            raise Http404("Document file is missing.")

        try:
            file_handle = file_to_serve.open("rb")
        except FileNotFoundError as exc:
            raise Http404("Document file is missing from storage.") from exc

        response = FileResponse(file_handle, as_attachment=False)  # Open in browser
        filename = file_to_serve.name.rsplit("/", 1)[-1]
        response["Content-Disposition"] = f'inline; filename="{get_valid_filename(smart_str(filename))}"'
        response["Content-Type"] = "application/pdf"
        return response


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

