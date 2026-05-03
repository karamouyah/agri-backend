"""
File responsibility: Processes HTTP API requests, checks permissions, queries models, and returns REST responses.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.db.models import Prefetch, Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.catalog.models import Category, Product, ProductList
from apps.catalog.serializers import (
    AdminProductSerializer,
    CategorySerializer,
    ControlledProductSerializer,
    ProductSerializer,
)
from apps.common.permissions import IsFarmer, IsMinistry
from apps.locations.models import Commune, Wilaya
from apps.users.models import Farmer, Farm


class CategoryViewSet(ModelViewSet):
    """Defines CategoryViewSet for this app and is used by the serializers, views, routes, or admin when imported."""
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer

    def get_permissions(self):
        """Handles get_permissions, using the declared parameters and returning the expected value or API response."""
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        return [IsMinistry()]


class AdminProductViewSet(ModelViewSet):
    """Defines AdminProductViewSet for this app and is used by the serializers, views, routes, or admin when imported."""
    queryset = Product.objects.select_related("category").all().order_by("category__name", "name")
    serializer_class = AdminProductSerializer
    permission_classes = [IsMinistry]

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        queryset = super().get_queryset()
        query = self.request.query_params.get("q", "").strip()
        category = self.request.query_params.get("category", "").strip()

        if query:
            queryset = queryset.filter(name__icontains=query)

        if category:
            category_filters = Q(category__name__iexact=category)
            if category.isdigit():
                category_filters |= Q(category_id=int(category))
            queryset = queryset.filter(category_filters)

        return queryset

    def perform_destroy(self, instance):
        """Handles perform_destroy, using the declared parameters and returning the expected value or API response."""
        listings = instance.listings.all()

        if listings.filter(order_items__isnull=False).exists():
            raise ValidationError({"detail": "This product cannot be deleted because it is linked to existing orders."})

        # Remove unused farmer listings first so the catalog product can be deleted safely.
        listings.delete()
        instance.delete()


class ProductViewSet(ModelViewSet):
    """Defines ProductViewSet for this app and is used by the serializers, views, routes, or admin when imported."""
    queryset = (
        ProductList.objects.select_related("product", "product__category", "farmer", "farmer__person")
        .prefetch_related(
            Prefetch(
                "farmer__farms",
                queryset=Farm.objects.select_related("wilaya", "commune").order_by("id"),
                to_attr="prefetched_farms",
            )
        )
        .filter(product__is_active=True)
        .all()
    )
    serializer_class = ProductSerializer

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        queryset = super().get_queryset()
        user = self.request.user
        query = self.request.query_params.get("q", "").strip()
        category = self.request.query_params.get("category")
        location = self.request.query_params.get("location")
        wilaya = self.request.query_params.get("wilaya")
        commune = self.request.query_params.get("commune")

        if getattr(user, "role", None) == user.Role.FARMER and hasattr(user, "farmer"):
            queryset = queryset.filter(farmer=user.farmer)

        if query:
            queryset = queryset.filter(
                Q(product__name__icontains=query)
                | Q(farmer__person__first_name__icontains=query)
                | Q(farmer__person__last_name__icontains=query)
            )
        if category:
            queryset = queryset.filter(product__category__name=category)
        if location:
            queryset = queryset.filter(
                Q(farmer__farms__location__icontains=location)
                | Q(farmer__farms__wilaya__name__icontains=location)
                | Q(farmer__farms__commune__name__icontains=location)
            )
        if wilaya:
            queryset = queryset.filter(farmer__farms__wilaya_id=wilaya)
        if commune:
            queryset = queryset.filter(farmer__farms__commune_id=commune)

        return queryset.distinct()

    def get_permissions(self):
        """Handles get_permissions, using the declared parameters and returning the expected value or API response."""
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsFarmer()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Handles perform_create, using the declared parameters and returning the expected value or API response."""
        user = self.request.user
        farmer = getattr(user, "farmer", None)
        if not farmer:
            farmer = Farmer.objects.create(person=user)
            if not farmer.farms.exists():
                Farm.objects.create(
                    farmer=farmer,
                    name=f"{user.first_name or 'Farmer'} Farm",
                    location=f"Farm address not set ({user.id})",
                )
        serializer.save(farmer=farmer)


class ControlledProductListView(generics.ListAPIView):
    """Defines ControlledProductListView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = ControlledProductSerializer
    permission_classes = [IsAuthenticated]
    queryset = Product.objects.select_related("category").filter(is_active=True).order_by("category__name", "name")

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        queryset = super().get_queryset()
        query = self.request.query_params.get("q", "").strip()
        category = self.request.query_params.get("category", "").strip()

        if query:
            queryset = queryset.filter(name__icontains=query)

        if category:
            queryset = queryset.filter(category__name__iexact=category)

        return queryset


class BuyerFilterOptionsView(APIView):
    """Defines BuyerFilterOptionsView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Handles get, using the declared parameters and returning the expected value or API response."""
        wilayas = list(Wilaya.objects.order_by("id").values("id", "code", "name"))
        communes = list(Commune.objects.select_related("wilaya").order_by("name").values("id", "name", "wilaya_id"))
        locations = list(
            Farm.objects.select_related("wilaya", "commune")
            .values_list("location", flat=True)
            .distinct()
        )
        return Response(
            {
                "categories": list(
                    Category.objects.filter(products__is_active=True).distinct().values_list("name", flat=True)
                ),
                "locations": sorted(set(locations)),
                "wilayas": wilayas,
                "communes": communes,
                "qualities": ["A"],
            }
        )


class RelatedProductsView(generics.ListAPIView):
    """Defines RelatedProductsView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        product_id = self.kwargs["product_id"]
        listing = ProductList.objects.select_related("product").filter(id=product_id).first()
        if not listing:
            return ProductList.objects.none()

        return (
            ProductList.objects.select_related("product", "product__category", "farmer", "farmer__person")
            .prefetch_related("farmer__farms")
            .filter(product__is_active=True)
            .filter(product__category=listing.product.category)
            .exclude(id=product_id)[:3]
        )
