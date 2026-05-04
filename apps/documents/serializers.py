from django.core.exceptions import DisallowedHost
from rest_framework import serializers

from apps.documents.models import VerificationDocument
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
        "approval_status": user.approval_status_slug,
    }


class VerificationDocumentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = VerificationDocument
        fields = [
            "id",
            "user",
            "role",
            "document_type",
            "file_url",
            "pdf_url",
            "file_name",
            "status",
            "admin_notes",
            "created_at",
            "updated_at",
        ]

    def get_user(self, obj):
        return user_summary(obj.user)

    def get_file_url(self, obj):
        if not obj.file:
            return ""
        request = self.context.get("request")
        url = f"/api/documents/{obj.id}/download/"
        if not request:
            return url
        try:
            return request.build_absolute_uri(url)
        except DisallowedHost:
            return url

    def get_pdf_url(self, obj):
        """Return URL to the converted PDF file if available."""
        if not obj.pdf_file:
            return ""
        request = self.context.get("request")
        url = f"/api/documents/{obj.id}/download-pdf/"
        if not request:
            return url
        try:
            return request.build_absolute_uri(url)
        except DisallowedHost:
            return url

    def get_file_name(self, obj):
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else ""


class VerificationDocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = ["document_type", "file"]

    def validate(self, attrs):
        user = self.context["request"].user
        if user.role not in {User.Role.BUYER, User.Role.TRANSPORTER, User.Role.FARMER}:
            raise serializers.ValidationError("Only buyers, transporters, and farmers can upload verification documents.")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return VerificationDocument.objects.create(
            user=user,
            role=user.role_slug,
            status=VerificationDocument.Status.PENDING,
            **validated_data,
        )


class AdminVerificationDocumentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = ["status", "admin_notes"]
        extra_kwargs = {
            "status": {"required": False},
            "admin_notes": {"required": False, "allow_blank": True},
        }
