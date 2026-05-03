from django.urls import path

from apps.reports.views import AdminReportDetailView, AdminReportsView, MyReportsView, ReportCreateView


urlpatterns = [
    path("", ReportCreateView.as_view(), name="report-create"),
    path("mine/", MyReportsView.as_view(), name="my-reports"),
    path("admin/", AdminReportsView.as_view(), name="admin-reports"),
    path("admin/<int:pk>/", AdminReportDetailView.as_view(), name="admin-report-detail"),
]
