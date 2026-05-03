"""
File responsibility: Defines database tables and relationships for this Django app.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.db import models

from apps.users.models import Farmer


class Category(models.Model):
    """Defines Category for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDCategory")
    name = models.CharField(max_length=100, db_column="Name")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Category"
        ordering = ["name"]

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return self.name


class Product(models.Model):
    """Defines Product for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDProduct")
    name = models.CharField(max_length=100, db_column="Name", unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, db_column="IDCategory", related_name="products")
    unit = models.CharField(max_length=20, db_column="Unit", default="kg")
    min_price = models.IntegerField(db_column="MinPrice", default=0)
    max_price = models.IntegerField(db_column="MaxPrice", default=0)
    image_data_url = models.TextField(blank=True, db_column="ImageDataUrl")
    is_active = models.BooleanField(db_column="IsActive", default=True)

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Product"
        ordering = ["name"]

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return self.name

    @property
    def suggested_price(self):
        """Handles suggested_price, using the declared parameters and returning the expected value or API response."""
        return None


class ProductList(models.Model):
    """Defines ProductList for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDProductList")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_column="IDProduct", related_name="listings")
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, db_column="IDFarmer", related_name="product_listings")
    quantity = models.IntegerField(default=0, db_column="Quantity")
    price = models.IntegerField(default=0, db_column="Price")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "ProductList"
        constraints = [
            models.UniqueConstraint(fields=["farmer", "product"], name="unique_farmer_product_listing"),
        ]

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return f"{self.product.name} ({self.farmer.person.email})"
