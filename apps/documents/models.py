from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


ALLOWED_DOCUMENT_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
MAX_DOCUMENT_SIZE = 5 * 1024 * 1024


def validate_verification_file(file):
    content_type = getattr(file, "content_type", "")
    if content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise ValidationError("Only JPG, PNG, WEBP, or PDF files are allowed.")

    if file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError("Document file size must be 5 MB or less.")


class VerificationDocument(models.Model):
    class Role(models.TextChoices):
        FARMER = "farmer", "Farmer"
        BUYER = "buyer", "Buyer"
        TRANSPORTER = "transporter", "Transporter"

    class DocumentType(models.TextChoices):
        ID_CARD = "ID_CARD", "ID card"
        LICENSE = "LICENSE", "License"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_documents",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    file = models.FileField(upload_to="verification_documents/%Y/%m/", validators=[validate_verification_file])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "status"], name="doc_user_status_idx"),
        ]

    def __str__(self):
        return f"VerificationDocument<{self.id}:{self.role}:{self.status}>"

