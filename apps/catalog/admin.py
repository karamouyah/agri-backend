"""
File responsibility: Registers Django models or admin URLs so staff can manage backend data.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.contrib import admin

from apps.catalog.models import Category, Product, ProductList


admin.site.register(Category)
admin.site.register(ProductList)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Defines ProductAdmin for this app and is used by the serializers, views, routes, or admin when imported."""
    list_display = ("name", "category", "unit", "min_price", "max_price", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)
