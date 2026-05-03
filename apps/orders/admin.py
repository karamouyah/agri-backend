"""
File responsibility: Registers Django models or admin URLs so staff can manage backend data.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.contrib import admin

from apps.orders.models import Order, OrderItem, Payment


admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
