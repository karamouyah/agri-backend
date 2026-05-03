"""
File responsibility: Stores static seed data that is imported by migrations, commands, or serializers.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
import json
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parents[3] / "shared" / "controlled-product-catalog.json"


def load_controlled_catalog():
    """Handles load_controlled_catalog, using the declared parameters and returning the expected value or API response."""
    with CATALOG_PATH.open("r", encoding="utf-8") as catalog_file:
        raw_catalog = json.load(catalog_file)

    normalized = []
    for index, item in enumerate(raw_catalog, start=1):
        normalized.append(
            {
                "id": index,
                "name": item["name"].strip(),
                "category": item["category"].strip(),
                "unit": (item.get("unit") or "kg").strip(),
                "min_price_dzd": int(item["min_price_dzd"]),
                "max_price_dzd": int(item["max_price_dzd"]),
                "is_active": bool(item.get("is_active", True)),
            }
        )

    return normalized


def sync_controlled_catalog(CategoryModel, ProductModel):
    """Handles sync_controlled_catalog, using the declared parameters and returning the expected value or API response."""
    catalog = load_controlled_catalog()
    allowed_names = set()
    category_cache = {}

    for item in catalog:
        category_name = item["category"]
        category = category_cache.get(category_name)
        if category is None:
            category, _ = CategoryModel.objects.get_or_create(name=category_name)
            category_cache[category_name] = category

        ProductModel.objects.update_or_create(
            name=item["name"],
            defaults={
                "category": category,
                "unit": item["unit"],
                "min_price": item["min_price_dzd"],
                "max_price": item["max_price_dzd"],
                "is_active": item["is_active"],
            },
        )
        allowed_names.add(item["name"])

    ProductModel.objects.exclude(name__in=allowed_names).update(is_active=False)

    return catalog
