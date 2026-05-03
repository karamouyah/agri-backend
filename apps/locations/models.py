"""
File responsibility: Defines database tables and relationships for this Django app.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.db import models


class Wilaya(models.Model):
    """Defines Wilaya for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.PositiveSmallIntegerField(primary_key=True, db_column="IDWilaya")
    code = models.CharField(max_length=2, unique=True, db_column="Code")
    name = models.CharField(max_length=100, unique=True, db_column="Name")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Wilaya"
        ordering = ["id"]

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return self.name


class Commune(models.Model):
    """Defines Commune for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.PositiveIntegerField(primary_key=True, db_column="IDCommune")
    wilaya = models.ForeignKey(
        Wilaya,
        on_delete=models.CASCADE,
        related_name="communes",
        db_column="IDWilaya",
    )
    name = models.CharField(max_length=120, db_column="Name")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Commune"
        ordering = ["wilaya_id", "name"]
        constraints = [
            models.UniqueConstraint(fields=["wilaya", "name"], name="unique_commune_name_per_wilaya"),
        ]

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return f"{self.name}, {self.wilaya.name}"

