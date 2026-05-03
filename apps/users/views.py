"""
File responsibility: Processes HTTP API requests, checks permissions, queries models, and returns REST responses.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from collections import defaultdict

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.common.permissions import IsMinistry
from apps.orders.models import OrderItem
from apps.users.models import Buyer, Farmer, Farm, JoinRequest, Transporter, User
from apps.users.serializers import (
    BuyerAccountSerializer,
    FarmerAccountSerializer,
    RegisterSerializer,
    TransporterAccountSerializer,
    UserApprovalUpdateSerializer,
    UserSerializer,
    UserTokenSerializer,
    clean_text,
    primary_farm,
)


class RegisterView(generics.CreateAPIView):
    """Defines RegisterView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class LoginView(TokenObtainPairView):
    """Defines LoginView for this app and is used by the serializers, views, routes, or admin when imported."""
    serializer_class = UserTokenSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RefreshView(TokenRefreshView):
    """Defines RefreshView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [AllowAny]


class CurrentUserView(APIView):
    """Defines CurrentUserView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Handles get, using the declared parameters and returning the expected value or API response."""
        return Response(UserSerializer(request.user).data)


class AdminUserViewSet(ModelViewSet):
    """Defines AdminUserViewSet for this app and is used by the serializers, views, routes, or admin when imported."""
    queryset = (
        User.objects.select_related(
            "farmer",
            "buyer",
            "buyer__wilaya",
            "buyer__commune",
            "transporter",
            "admin_profile",
        )
        .prefetch_related(
            "farmer__farms__wilaya",
            "farmer__farms__commune",
            "transporter__delivery_wilayas",
            "verification_documents",
        )
        .all()
        .order_by("-date_joined")
    )
    serializer_class = UserSerializer
    permission_classes = [IsMinistry]

    def get_queryset(self):
        """Handles get_queryset, using the declared parameters and returning the expected value or API response."""
        queryset = super().get_queryset()
        role = clean_text(self.request.query_params.get("role")).lower()
        approval_status = clean_text(self.request.query_params.get("approval_status")).lower()
        wilaya = clean_text(self.request.query_params.get("wilaya"))

        if role:
            role_code = User.role_from_slug(role)
            if role_code is not None:
                queryset = queryset.filter(role=role_code)
            else:
                queryset = queryset.none()

        if approval_status:
            status_code = User.status_from_slug(approval_status)
            if status_code is not None:
                queryset = queryset.filter(status=status_code)
            else:
                queryset = queryset.none()

        if wilaya:
            wilaya_filter = (
                Q(farmer__farms__wilaya_id=wilaya)
                | Q(buyer__wilaya_id=wilaya)
                | Q(transporter__delivery_wilayas__id=wilaya)
            )

            if not wilaya.isdigit():
                wilaya_filter = (
                    Q(farmer__farms__wilaya__name__iexact=wilaya)
                    | Q(buyer__wilaya__name__iexact=wilaya)
                    | Q(transporter__delivery_wilayas__name__iexact=wilaya)
                )

            queryset = queryset.filter(wilaya_filter)

        return queryset.distinct()

    def get_serializer_class(self):
        """Handles get_serializer_class, using the declared parameters and returning the expected value or API response."""
        if self.action in {"partial_update", "update"}:
            return UserApprovalUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=["get"], url_path="pending")
    def pending_accounts(self, request):
        """Handles pending_accounts, using the declared parameters and returning the expected value or API response."""
        queryset = self.get_queryset().filter(status=User.Status.PENDING)
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @staticmethod
    def _join_request_status(user_status):
        """Handles _join_request_status, using the declared parameters and returning the expected value or API response."""
        if user_status == User.Status.APPROVED:
            return JoinRequest.RequestStatus.APPROVED
        if user_status == User.Status.REJECTED:
            return JoinRequest.RequestStatus.REJECTED
        return JoinRequest.RequestStatus.PENDING

    def _set_approval(self, user, approval_status):
        """Handles _set_approval, using the declared parameters and returning the expected value or API response."""
        if user.role == User.Role.MINISTRY and approval_status != User.Status.APPROVED:
            return Response(
                {"detail": "Ministry accounts cannot be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.status = approval_status
        user.save(update_fields=["status"])

        request_row = JoinRequest.objects.filter(email__iexact=user.email).order_by("-request_date", "-id").first()
        if request_row:
            request_row.status = self._join_request_status(approval_status)
            request_row.review_date = timezone.now()
            if hasattr(self.request.user, "admin_profile"):
                request_row.admin = self.request.user.admin_profile
            request_row.save(update_fields=["status", "review_date", "admin"])

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_account(self, request, pk=None):
        """Handles approve_account, using the declared parameters and returning the expected value or API response."""
        user = self.get_object()
        return self._set_approval(user, User.Status.APPROVED)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject_account(self, request, pk=None):
        """Handles reject_account, using the declared parameters and returning the expected value or API response."""
        user = self.get_object()
        return self._set_approval(user, User.Status.REJECTED)


class NationalStatsView(APIView):
    """Defines NationalStatsView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsMinistry]

    def get(self, request):
        """Handles get, using the declared parameters and returning the expected value or API response."""
        grouped = (
            User.objects.filter(status=User.Status.APPROVED)
            .values("role")
            .annotate(total=Count("id"))
        )
        totals = {row["role"]: row["total"] for row in grouped}

        region_rows = (
            OrderItem.objects.values("order__pickup_wilaya__name", "order__pickup_address")
            .annotate(volume=Sum("quantity"))
            .order_by("order__pickup_wilaya__name", "order__pickup_address")
        )
        regional_sales = [
            {
                "region": row["order__pickup_wilaya__name"] or row["order__pickup_address"] or "Unknown",
                "volume": row["volume"] or 0,
            }
            for row in region_rows
        ]

        total_volume = sum((row["volume"] or 0) for row in regional_sales)

        return Response(
            {
                "summary": {
                    "totalSalesVolumeTons": total_volume,
                    "activeFarmers": totals.get(User.Role.FARMER, 0),
                    "activeBuyers": totals.get(User.Role.BUYER, 0),
                    "activeTransporters": totals.get(User.Role.TRANSPORTER, 0),
                },
                "regionalSales": regional_sales,
                "priceTrends": [
                    {"month": "Jan", "tomatoes": 10, "oranges": 12, "potatoes": 6},
                    {"month": "Feb", "tomatoes": 9, "oranges": 11, "potatoes": 5},
                    {"month": "Mar", "tomatoes": 11, "oranges": 13, "potatoes": 6},
                ],
            },
            status=status.HTTP_200_OK,
        )


class GenerateReportView(APIView):
    """Defines GenerateReportView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsMinistry]

    def get(self, request):
        """Handles get, using the declared parameters and returning the expected value or API response."""
        region = clean_text(request.query_params.get("region"))
        category = clean_text(request.query_params.get("category"))

        items = OrderItem.objects.select_related(
            "order",
            "order__pickup_wilaya",
            "product_list__product__category",
        )
        if region:
            if region.isdigit():
                items = items.filter(order__pickup_wilaya_id=int(region))
            else:
                items = items.filter(order__pickup_wilaya__name__iexact=region)
        if category:
            items = items.filter(product_list__product__category__name__iexact=category)

        grouped = defaultdict(lambda: {"volume": 0, "revenue": 0})
        for item in items:
            region_name = item.order.pickup_wilaya.name if item.order.pickup_wilaya else item.order.pickup_address or "Unknown"
            category_name = item.product_list.product.category.name
            key = (region_name, category_name)
            grouped[key]["volume"] += item.quantity
            grouped[key]["revenue"] += item.total_items_price

        rows = [
            {
                "region": region_name,
                "category": category_name,
                "volume": agg["volume"],
                "revenue": round(float(agg["revenue"]), 2),
            }
            for (region_name, category_name), agg in grouped.items()
        ]

        return Response({"params": {"region": region, "category": category}, "rows": rows})


class FarmProfileView(APIView):
    """Defines FarmProfileView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsAuthenticated]

    def _ensure_farmer_farm(self, user):
        """Handles _ensure_farmer_farm, using the declared parameters and returning the expected value or API response."""
        farmer = getattr(user, "farmer", None)
        if not farmer:
            farmer = Farmer.objects.create(person=user)

        farm = primary_farm(farmer)
        if not farm:
            farm = Farm.objects.create(
                farmer=farmer,
                name=f"{user.first_name or 'Farmer'} Farm",
                location=f"Farm address not set ({user.id})",
            )

        return farmer, farm

    def get(self, request):
        """Handles get, using the declared parameters and returning the expected value or API response."""
        user = request.user
        if user.role != User.Role.FARMER:
            return Response({"detail": "Only farmers can access profile."}, status=status.HTTP_403_FORBIDDEN)

        self._ensure_farmer_farm(user)
        return Response(FarmerAccountSerializer().to_representation(user))

    def patch(self, request):
        """Handles patch, using the declared parameters and returning the expected value or API response."""
        user = request.user
        if user.role != User.Role.FARMER:
            return Response({"detail": "Only farmers can update profile."}, status=status.HTTP_403_FORBIDDEN)

        self._ensure_farmer_farm(user)
        serializer = FarmerAccountSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            serializer.update(user, serializer.validated_data)
        except IntegrityError:
            return Response(
                {
                    "farmAddress": (
                        "A farmer is already registered with this farm address. "
                        "Please use a different farm address."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(serializer.to_representation(user))


class BuyerProfileView(APIView):
    """Defines BuyerProfileView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Handles get, using the declared parameters and returning the expected value or API response."""
        if request.user.role != User.Role.BUYER:
            return Response({"detail": "Only buyers can access profile."}, status=status.HTTP_403_FORBIDDEN)

        if not hasattr(request.user, "buyer"):
            Buyer.objects.create(person=request.user)
        return Response(BuyerAccountSerializer().to_representation(request.user))

    def patch(self, request):
        """Handles patch, using the declared parameters and returning the expected value or API response."""
        if request.user.role != User.Role.BUYER:
            return Response({"detail": "Only buyers can update profile."}, status=status.HTTP_403_FORBIDDEN)

        if not hasattr(request.user, "buyer"):
            Buyer.objects.create(person=request.user)

        serializer = BuyerAccountSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        return Response(serializer.to_representation(request.user))


class TransporterProfileView(APIView):
    """Defines TransporterProfileView for this app and is used by the serializers, views, routes, or admin when imported."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Handles get, using the declared parameters and returning the expected value or API response."""
        if request.user.role != User.Role.TRANSPORTER:
            return Response({"detail": "Only transporters can access profile."}, status=status.HTTP_403_FORBIDDEN)

        if not hasattr(request.user, "transporter"):
            Transporter.objects.create(person=request.user)
        return Response(TransporterAccountSerializer().to_representation(request.user))

    def patch(self, request):
        """Handles patch, using the declared parameters and returning the expected value or API response."""
        if request.user.role != User.Role.TRANSPORTER:
            return Response({"detail": "Only transporters can update profile."}, status=status.HTTP_403_FORBIDDEN)

        if not hasattr(request.user, "transporter"):
            Transporter.objects.create(person=request.user)

        serializer = TransporterAccountSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        return Response(serializer.to_representation(request.user))
