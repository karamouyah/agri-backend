from django.urls import path

from apps.documents.views import (
    AdminVerificationDocumentDetailView,
    AdminVerificationDocumentsView,
    MyVerificationDocumentsView,
    VerificationDocumentUploadView,
)


urlpatterns = [
    path("upload/", VerificationDocumentUploadView.as_view(), name="document-upload"),
    path("mine/", MyVerificationDocumentsView.as_view(), name="my-documents"),
    path("admin/", AdminVerificationDocumentsView.as_view(), name="admin-documents"),
    path("admin/<int:pk>/", AdminVerificationDocumentDetailView.as_view(), name="admin-document-detail"),
]
