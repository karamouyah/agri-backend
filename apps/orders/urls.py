"""
File responsibility: Maps app-level API paths to the views and viewsets in this Django app.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.urls import path

from apps.orders.views import AdminOrdersView, CheckoutView, MyInvoicesView, MyOrdersView, UpdateOrderStatusView

urlpatterns = [
    path("admin/", AdminOrdersView.as_view(), name="admin-orders"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("mine/", MyOrdersView.as_view(), name="my-orders"),
    path("<str:public_id>/status/", UpdateOrderStatusView.as_view(), name="order-status"),
    path("invoices/mine/", MyInvoicesView.as_view(), name="my-invoices"),
]
