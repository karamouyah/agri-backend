from django.contrib import admin

from apps.documents.models import VerificationDocument


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "document_type", "status", "created_at")
    list_filter = ("role", "document_type", "status")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at")

