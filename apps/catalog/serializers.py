"""
File responsibility: Validates request data and converts Django models into JSON API responses.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from rest_framework import serializers

from apps.catalog.models import Category, Product, ProductList
from apps.users.models import Farmer


class CategorySerializer(serializers.ModelSerializer):
    """Defines CategorySerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Category
        fields = ["id", "name"]


class AdminProductSerializer(serializers.ModelSerializer):
    """Defines AdminProductSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.CharField(source="category.name", read_only=True)
    image_data_url = serializers.CharField(required=False, allow_blank=True, write_only=True)
    image_url = serializers.SerializerMethodField()
    min_price_dzd = serializers.IntegerField(source="min_price", min_value=0)
    max_price_dzd = serializers.IntegerField(source="max_price", min_value=0)
    suggested_price_dzd = serializers.IntegerField(
        source="suggested_price",
        min_value=0,
        required=False,
        allow_null=True,
    )

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "category_name",
            "unit",
            "min_price_dzd",
            "max_price_dzd",
            "suggested_price_dzd",
            "image_data_url",
            "image_url",
            "is_active",
        ]
        read_only_fields = ["unit", "is_active", "category_name", "image_url"]

    def get_image_url(self, obj):
        """Returns the stored product image data URL when one exists."""
        return obj.image_data_url or ""

    def validate_name(self, value):
        """Handles validate_name, using the declared parameters and returning the expected value or API response."""
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Product name is required.")

        queryset = Product.objects.filter(name__iexact=name)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError("A product with this name already exists.")

        return name

    def validate_image_data_url(self, value):
        """Accepts compact browser-created image data URLs for product catalog photos."""
        if not value:
            return ""

        if not value.startswith("data:image/"):
            raise serializers.ValidationError("Product picture must be an image file.")
        if len(value) > 2_000_000:
            raise serializers.ValidationError("Product picture must be 1.5 MB or smaller.")

        return value

    def validate(self, attrs):
        """Handles validate, using the declared parameters and returning the expected value or API response."""
        min_price = attrs.get("min_price", self.instance.min_price if self.instance else 0)
        max_price = attrs.get("max_price", self.instance.max_price if self.instance else 0)
        suggested_price = attrs.get("suggested_price", self.instance.suggested_price if self.instance else None)

        if max_price < min_price:
            raise serializers.ValidationError({"max_price_dzd": "Maximum price must be greater than or equal to minimum price."})

        if suggested_price is not None and not (min_price <= suggested_price <= max_price):
            raise serializers.ValidationError(
                {"suggested_price_dzd": "Suggested price must be between the minimum and maximum prices."}
            )

        return attrs

    def create(self, validated_data):
        """Handles create, using the declared parameters and returning the expected value or API response."""
        validated_data.pop("suggested_price", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Handles update, using the declared parameters and returning the expected value or API response."""
        validated_data.pop("suggested_price", None)
        return super().update(instance, validated_data)


class ProductSerializer(serializers.ModelSerializer):
    """Defines ProductSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    name = serializers.CharField(source="product.name", read_only=True)
    category = serializers.IntegerField(source="product.category_id", read_only=True)
    category_name = serializers.CharField(source="product.category.name", read_only=True)
    unit = serializers.CharField(source="product.unit", read_only=True)
    min_price = serializers.IntegerField(source="product.min_price", read_only=True)
    max_price = serializers.IntegerField(source="product.max_price", read_only=True)
    min_price_dzd = serializers.IntegerField(source="product.min_price", read_only=True)
    max_price_dzd = serializers.IntegerField(source="product.max_price", read_only=True)
    is_active = serializers.BooleanField(source="product.is_active", read_only=True)
    currency = serializers.SerializerMethodField()
    price = serializers.IntegerField(min_value=0)
    quantity_available = serializers.IntegerField(source="quantity", min_value=0)
    farmer_name = serializers.SerializerMethodField()
    farmer_region = serializers.SerializerMethodField()
    farmer_wilaya_id = serializers.SerializerMethodField()
    farmer_wilaya = serializers.SerializerMethodField()
    farmer_commune_id = serializers.SerializerMethodField()
    farmer_commune = serializers.SerializerMethodField()
    quality = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = ProductList
        fields = [
            "id",
            "product",
            "name",
            "category",
            "category_name",
            "unit",
            "min_price",
            "max_price",
            "min_price_dzd",
            "max_price_dzd",
            "is_active",
            "currency",
            "price",
            "quantity_available",
            "farmer_name",
            "farmer_region",
            "farmer_wilaya_id",
            "farmer_wilaya",
            "farmer_commune_id",
            "farmer_commune",
            "quality",
            "image_url",
            "description",
            "status",
        ]

    def validate_price(self, value):
        """Handles validate_price, using the declared parameters and returning the expected value or API response."""
        product = self.initial_data.get("product")

        if product is not None:
            target = Product.objects.filter(id=product).first()
        elif self.instance:
            target = self.instance.product
        else:
            target = None

        if not target:
            return value

        if not target.is_active:
            raise serializers.ValidationError("This product is not available in the approved catalog.")

        if value < target.min_price or value > target.max_price:
            raise serializers.ValidationError(
                f"Price must be between {target.min_price} and {target.max_price} DZD"
            )

        return value

    def get_currency(self, _obj):
        """Handles get_currency, using the declared parameters and returning the expected value or API response."""
        return "DZD"

    def _get_primary_farm(self, obj):
        """Handles _get_primary_farm, using the declared parameters and returning the expected value or API response."""
        prefetched_farms = getattr(obj.farmer, "prefetched_farms", None)
        if prefetched_farms is not None:
            return prefetched_farms[0] if prefetched_farms else None

        return obj.farmer.farms.select_related("wilaya", "commune").order_by("id").first()

    def get_farmer_name(self, obj):
        """Handles get_farmer_name, using the declared parameters and returning the expected value or API response."""
        full = f"{obj.farmer.person.first_name} {obj.farmer.person.last_name}".strip()
        return full or obj.farmer.person.email

    def get_farmer_region(self, obj):
        """Handles get_farmer_region, using the declared parameters and returning the expected value or API response."""
        farm = self._get_primary_farm(obj)
        return farm.location_label if farm else "Unknown"

    def get_farmer_wilaya_id(self, obj):
        """Handles get_farmer_wilaya_id, using the declared parameters and returning the expected value or API response."""
        farm = self._get_primary_farm(obj)
        return farm.wilaya_id if farm else None

    def get_farmer_wilaya(self, obj):
        """Handles get_farmer_wilaya, using the declared parameters and returning the expected value or API response."""
        farm = self._get_primary_farm(obj)
        return farm.wilaya.name if farm and farm.wilaya else ""

    def get_farmer_commune_id(self, obj):
        """Handles get_farmer_commune_id, using the declared parameters and returning the expected value or API response."""
        farm = self._get_primary_farm(obj)
        return farm.commune_id if farm else None

    def get_farmer_commune(self, obj):
        """Handles get_farmer_commune, using the declared parameters and returning the expected value or API response."""
        farm = self._get_primary_farm(obj)
        return farm.commune.name if farm and farm.commune else ""

    def get_quality(self, _obj):
        """Handles get_quality, using the declared parameters and returning the expected value or API response."""
        return "A"

    def get_image_url(self, _obj):
        """Handles get_image_url, using the declared parameters and returning the expected value or API response."""
        product = getattr(_obj, "product", None)
        return product.image_data_url if product else ""

    def get_description(self, _obj):
        """Handles get_description, using the declared parameters and returning the expected value or API response."""
        return ""

    def get_status(self, obj):
        """Handles get_status, using the declared parameters and returning the expected value or API response."""
        return "available" if obj.quantity > 0 else "out of stock"

    def create(self, validated_data):
        """Handles create, using the declared parameters and returning the expected value or API response."""
        product = validated_data["product"]
        farmer = validated_data["farmer"]
        if ProductList.objects.filter(product=product, farmer=farmer).exists():
            raise serializers.ValidationError(
                {"product": "You already listed this product. Please edit the existing listing."}
            )
        return ProductList.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Handles update, using the declared parameters and returning the expected value or API response."""
        target_product = validated_data.get("product", instance.product)

        if not target_product.is_active:
            raise serializers.ValidationError(
                {"product": "This product is not available in the approved catalog."}
            )

        if (
            ProductList.objects.filter(product=target_product, farmer=instance.farmer)
            .exclude(id=instance.id)
            .exists()
        ):
            raise serializers.ValidationError(
                {"product": "You already listed this product. Please edit the existing listing."}
            )

        if "product" in validated_data:
            instance.product = target_product

        if "price" in validated_data:
            instance.price = validated_data["price"]
        if "quantity" in validated_data:
            instance.quantity = validated_data["quantity"]

        instance.save(update_fields=["product", "price", "quantity"])
        return instance


class ControlledProductSerializer(serializers.ModelSerializer):
    """Defines ControlledProductSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    category = serializers.CharField(source="category.name", read_only=True)
    min_price_dzd = serializers.IntegerField(source="min_price", read_only=True)
    max_price_dzd = serializers.IntegerField(source="max_price", read_only=True)
    currency = serializers.SerializerMethodField()

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "unit",
            "min_price",
            "max_price",
            "min_price_dzd",
            "max_price_dzd",
            "is_active",
            "currency",
        ]

    def get_currency(self, _obj):
        """Handles get_currency, using the declared parameters and returning the expected value or API response."""
        return "DZD"
