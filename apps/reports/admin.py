from django.contrib import admin

from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reporter", "category", "status", "created_at")
    list_filter = ("category", "status", "created_at")
    search_fields = ("reason", "description", "reporter__email", "reported_user__email")
