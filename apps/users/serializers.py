"""
File responsibility: Validates request data and converts Django models into JSON API responses.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
import re

from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.locations.models import Commune, Wilaya
from apps.users.models import Buyer, Farmer, Farm, JoinRequest, Transporter, User


PHONE_REGEX = re.compile(r"^\+?[0-9()\-\s]{7,20}$")


def clean_text(value):
    """Handles clean_text, using the declared parameters and returning the expected value or API response."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def parse_int(value):
    """Handles parse_int, using the declared parameters and returning the expected value or API response."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_int_list(value):
    """Handles parse_int_list, using the declared parameters and returning the expected value or API response."""
    if value in (None, ""):
        return []
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",") if item.strip()]
    else:
        raw_items = list(value)

    results = []
    for item in raw_items:
        parsed = parse_int(item)
        if parsed is not None:
            results.append(parsed)
    return results


def primary_farm(farmer):
    """Handles primary_farm, using the declared parameters and returning the expected value or API response."""
    return farmer.farms.select_related("wilaya", "commune").order_by("id").first()


def compose_location_label(commune=None, wilaya=None):
    """Handles compose_location_label, using the declared parameters and returning the expected value or API response."""
    if commune and wilaya:
        return f"{commune.name}, {wilaya.name}"
    if commune:
        return commune.name
    if wilaya:
        return wilaya.name
    return ""


def compose_structured_address(base_address="", commune=None, wilaya=None):
    """Handles compose_structured_address, using the declared parameters and returning the expected value or API response."""
    parts = [clean_text(base_address), commune.name if commune else "", wilaya.name if wilaya else ""]
    return ", ".join([part for part in parts if part])


class LocationValidationMixin:
    """Defines LocationValidationMixin for this app and is used by the serializers, views, routes, or admin when imported."""
    wilaya_field_names = ("wilaya_id", "wilayaId", "wilaya")
    commune_field_names = ("commune_id", "communeId", "commune")

    def _extract_scalar(self, attrs, names):
        """Handles _extract_scalar, using the declared parameters and returning the expected value or API response."""
        for name in names:
            if name in attrs:
                return attrs.get(name)
        return None

    def _extract_location_pair(self, attrs, *, required):
        """Handles _extract_location_pair, using the declared parameters and returning the expected value or API response."""
        wilaya_id = parse_int(self._extract_scalar(attrs, self.wilaya_field_names))
        commune_id = parse_int(self._extract_scalar(attrs, self.commune_field_names))

        if not required and wilaya_id is None and commune_id is None:
            return None, None

        errors = {}
        wilaya = Wilaya.objects.filter(id=wilaya_id).first() if wilaya_id is not None else None
        commune = Commune.objects.select_related("wilaya").filter(id=commune_id).first() if commune_id is not None else None

        if wilaya_id is None:
            errors["wilaya_id"] = "Wilaya is required."
        elif not wilaya:
            errors["wilaya_id"] = "Selected wilaya is invalid."

        if commune_id is None:
            errors["commune_id"] = "Commune is required."
        elif not commune:
            errors["commune_id"] = "Selected commune is invalid."
        elif wilaya and commune.wilaya_id != wilaya.id:
            errors["commune_id"] = "Selected commune does not belong to the wilaya."

        if errors:
            raise serializers.ValidationError(errors)

        attrs["_wilaya"] = wilaya
        attrs["_commune"] = commune
        attrs["wilaya_id"] = wilaya.id
        attrs["commune_id"] = commune.id
        return wilaya, commune

    def _extract_delivery_wilayas(self, attrs, *, required):
        """Handles _extract_delivery_wilayas, using the declared parameters and returning the expected value or API response."""
        delivery_ids = []
        for key in ("delivery_wilaya_ids", "deliveryWilayaIds", "delivery_wilayas"):
            if key in attrs:
                delivery_ids = parse_int_list(attrs.get(key))
                break

        if not delivery_ids and not required:
            attrs["_delivery_wilayas"] = []
            attrs["delivery_wilaya_ids"] = []
            return []

        if not delivery_ids:
            raise serializers.ValidationError(
                {"delivery_wilaya_ids": "At least one delivery wilaya is required."}
            )

        wilayas = list(Wilaya.objects.filter(id__in=delivery_ids).order_by("id"))
        if len(wilayas) != len(set(delivery_ids)):
            raise serializers.ValidationError(
                {"delivery_wilaya_ids": "One or more selected delivery wilayas are invalid."}
            )

        attrs["_delivery_wilayas"] = wilayas
        attrs["delivery_wilaya_ids"] = [wilaya.id for wilaya in wilayas]
        return wilayas


class FarmerProfileSerializer(serializers.ModelSerializer):
    """Defines FarmerProfileSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    phone_number = serializers.CharField(source="person.phone_number", read_only=True)
    farm_address = serializers.SerializerMethodField()
    farm_name = serializers.SerializerMethodField()
    wilaya_id = serializers.SerializerMethodField()
    wilaya_name = serializers.SerializerMethodField()
    commune_id = serializers.SerializerMethodField()
    commune_name = serializers.SerializerMethodField()
    location_label = serializers.SerializerMethodField()

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Farmer
        fields = [
            "phone_number",
            "farm_name",
            "farm_address",
            "wilaya_id",
            "wilaya_name",
            "commune_id",
            "commune_name",
            "location_label",
        ]

    def get_farm_name(self, obj):
        """Handles get_farm_name, using the declared parameters and returning the expected value or API response."""
        farm = primary_farm(obj)
        return farm.name if farm else ""

    def get_farm_address(self, obj):
        """Handles get_farm_address, using the declared parameters and returning the expected value or API response."""
        farm = primary_farm(obj)
        return farm.location if farm else ""

    def get_wilaya_id(self, obj):
        """Handles get_wilaya_id, using the declared parameters and returning the expected value or API response."""
        farm = primary_farm(obj)
        return farm.wilaya_id if farm else None

    def get_wilaya_name(self, obj):
        """Handles get_wilaya_name, using the declared parameters and returning the expected value or API response."""
        farm = primary_farm(obj)
        return farm.wilaya.name if farm and farm.wilaya else ""

    def get_commune_id(self, obj):
        """Handles get_commune_id, using the declared parameters and returning the expected value or API response."""
        farm = primary_farm(obj)
        return farm.commune_id if farm else None

    def get_commune_name(self, obj):
        """Handles get_commune_name, using the declared parameters and returning the expected value or API response."""
        farm = primary_farm(obj)
        return farm.commune.name if farm and farm.commune else ""

    def get_location_label(self, obj):
        """Handles get_location_label, using the declared parameters and returning the expected value or API response."""
        farm = primary_farm(obj)
        return farm.location_label if farm else ""


class TransporterProfileSerializer(serializers.ModelSerializer):
    """Defines TransporterProfileSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    phone_number = serializers.CharField(source="person.phone_number", read_only=True)
    vehicle = serializers.CharField(source="vehicle_type", read_only=True)
    service_area = serializers.CharField(read_only=True)
    capacity = serializers.IntegerField(read_only=True)
    max_load_kg = serializers.IntegerField(read_only=True)
    average_rating = serializers.IntegerField(read_only=True)
    total_reviews = serializers.IntegerField(read_only=True)
    delivery_wilayas = serializers.SerializerMethodField()
    delivery_wilaya_ids = serializers.SerializerMethodField()

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Transporter
        fields = [
            "phone_number",
            "vehicle",
            "service_area",
            "capacity",
            "max_load_kg",
            "average_rating",
            "total_reviews",
            "delivery_wilayas",
            "delivery_wilaya_ids",
        ]

    def get_delivery_wilayas(self, obj):
        """Handles get_delivery_wilayas, using the declared parameters and returning the expected value or API response."""
        return [
            {"id": wilaya.id, "code": wilaya.code, "name": wilaya.name}
            for wilaya in obj.delivery_wilayas.order_by("id")
        ]

    def get_delivery_wilaya_ids(self, obj):
        """Handles get_delivery_wilaya_ids, using the declared parameters and returning the expected value or API response."""
        return list(obj.delivery_wilayas.order_by("id").values_list("id", flat=True))


class BuyerProfileSerializer(serializers.ModelSerializer):
    """Defines BuyerProfileSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    phone_number = serializers.CharField(source="person.phone_number", read_only=True)
    address = serializers.SerializerMethodField()
    street_address = serializers.CharField(source="person.address", read_only=True)
    wilaya_id = serializers.IntegerField(read_only=True)
    wilaya_name = serializers.CharField(source="wilaya.name", read_only=True)
    commune_id = serializers.IntegerField(read_only=True)
    commune_name = serializers.CharField(source="commune.name", read_only=True)
    location_label = serializers.SerializerMethodField()

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = Buyer
        fields = [
            "phone_number",
            "address",
            "street_address",
            "wilaya_id",
            "wilaya_name",
            "commune_id",
            "commune_name",
            "location_label",
        ]

    def get_address(self, obj):
        """Handles get_address, using the declared parameters and returning the expected value or API response."""
        return compose_structured_address(obj.person.address, obj.commune, obj.wilaya)

    def get_location_label(self, obj):
        """Handles get_location_label, using the declared parameters and returning the expected value or API response."""
        return obj.location_label


class UserSerializer(serializers.ModelSerializer):
    """Defines UserSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    approval_status = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    personal_picture_url = serializers.CharField(read_only=True)
    phone_number = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    farm_address = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    wilaya_id = serializers.SerializerMethodField()
    wilaya_name = serializers.SerializerMethodField()
    commune_id = serializers.SerializerMethodField()
    commune_name = serializers.SerializerMethodField()
    location_label = serializers.SerializerMethodField()
    max_load_kg = serializers.SerializerMethodField()
    delivery_wilayas = serializers.SerializerMethodField()
    delivery_wilaya_ids = serializers.SerializerMethodField()
    verification_documents_count = serializers.SerializerMethodField()
    verification_documents_status = serializers.SerializerMethodField()

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role",
            "status",
            "approval_status",
            "first_name",
            "last_name",
            "personal_picture_url",
            "profile",
            "phone_number",
            "phone",
            "farm_address",
            "vehicle",
            "address",
            "wilaya_id",
            "wilaya_name",
            "commune_id",
            "commune_name",
            "location_label",
            "max_load_kg",
            "delivery_wilayas",
            "delivery_wilaya_ids",
            "verification_documents_count",
            "verification_documents_status",
        ]

    def get_name(self, obj):
        """Handles get_name, using the declared parameters and returning the expected value or API response."""
        full = f"{obj.first_name} {obj.last_name}".strip()
        return full or obj.username or obj.email

    def get_role(self, obj):
        """Handles get_role, using the declared parameters and returning the expected value or API response."""
        return obj.role_slug

    def get_approval_status(self, obj):
        """Handles get_approval_status, using the declared parameters and returning the expected value or API response."""
        return obj.approval_status_slug

    def get_profile(self, obj):
        """Handles get_profile, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.FARMER and hasattr(obj, "farmer"):
            return FarmerProfileSerializer(obj.farmer).data
        if obj.role == User.Role.TRANSPORTER and hasattr(obj, "transporter"):
            return TransporterProfileSerializer(obj.transporter).data
        if obj.role == User.Role.BUYER and hasattr(obj, "buyer"):
            return BuyerProfileSerializer(obj.buyer).data
        return None

    def get_phone_number(self, obj):
        """Handles get_phone_number, using the declared parameters and returning the expected value or API response."""
        return obj.phone_number

    def get_phone(self, obj):
        """Handles get_phone, using the declared parameters and returning the expected value or API response."""
        return obj.phone_number

    def get_farm_address(self, obj):
        """Handles get_farm_address, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.FARMER and hasattr(obj, "farmer"):
            farm = primary_farm(obj.farmer)
            return farm.location if farm else ""
        return ""

    def get_vehicle(self, obj):
        """Handles get_vehicle, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.TRANSPORTER and hasattr(obj, "transporter"):
            return obj.transporter.vehicle_type
        return ""

    def get_address(self, obj):
        """Handles get_address, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.BUYER and hasattr(obj, "buyer"):
            return compose_structured_address(obj.address, obj.buyer.commune, obj.buyer.wilaya)
        return obj.address

    def get_wilaya_id(self, obj):
        """Handles get_wilaya_id, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.FARMER and hasattr(obj, "farmer"):
            farm = primary_farm(obj.farmer)
            return farm.wilaya_id if farm else None
        if obj.role == User.Role.BUYER and hasattr(obj, "buyer"):
            return obj.buyer.wilaya_id
        return None

    def get_wilaya_name(self, obj):
        """Handles get_wilaya_name, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.FARMER and hasattr(obj, "farmer"):
            farm = primary_farm(obj.farmer)
            return farm.wilaya.name if farm and farm.wilaya else ""
        if obj.role == User.Role.BUYER and hasattr(obj, "buyer") and obj.buyer.wilaya:
            return obj.buyer.wilaya.name
        return ""

    def get_commune_id(self, obj):
        """Handles get_commune_id, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.FARMER and hasattr(obj, "farmer"):
            farm = primary_farm(obj.farmer)
            return farm.commune_id if farm else None
        if obj.role == User.Role.BUYER and hasattr(obj, "buyer"):
            return obj.buyer.commune_id
        return None

    def get_commune_name(self, obj):
        """Handles get_commune_name, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.FARMER and hasattr(obj, "farmer"):
            farm = primary_farm(obj.farmer)
            return farm.commune.name if farm and farm.commune else ""
        if obj.role == User.Role.BUYER and hasattr(obj, "buyer") and obj.buyer.commune:
            return obj.buyer.commune.name
        return ""

    def get_location_label(self, obj):
        """Handles get_location_label, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.FARMER and hasattr(obj, "farmer"):
            farm = primary_farm(obj.farmer)
            return farm.location_label if farm else ""
        if obj.role == User.Role.BUYER and hasattr(obj, "buyer"):
            return obj.buyer.location_label
        if obj.role == User.Role.TRANSPORTER and hasattr(obj, "transporter"):
            return obj.transporter.coverage_label
        return clean_text(obj.address)

    def get_max_load_kg(self, obj):
        """Handles get_max_load_kg, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.TRANSPORTER and hasattr(obj, "transporter"):
            return obj.transporter.max_load_kg
        return None

    def get_delivery_wilayas(self, obj):
        """Handles get_delivery_wilayas, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.TRANSPORTER and hasattr(obj, "transporter"):
            return TransporterProfileSerializer(obj.transporter).data["delivery_wilayas"]
        return []

    def get_delivery_wilaya_ids(self, obj):
        """Handles get_delivery_wilaya_ids, using the declared parameters and returning the expected value or API response."""
        if obj.role == User.Role.TRANSPORTER and hasattr(obj, "transporter"):
            return TransporterProfileSerializer(obj.transporter).data["delivery_wilaya_ids"]
        return []

    def get_verification_documents_count(self, obj):
        return obj.verification_documents.count() if obj.role in {User.Role.BUYER, User.Role.TRANSPORTER} else 0

    def get_verification_documents_status(self, obj):
        if obj.role not in {User.Role.BUYER, User.Role.TRANSPORTER}:
            return "not_required"

        documents = list(obj.verification_documents.all())
        if not documents:
            return "missing"
        if any(document.status == "rejected" for document in documents):
            return "rejected"
        if any(document.status == "pending" for document in documents):
            return "pending"
        if all(document.status == "approved" for document in documents):
            return "approved"
        return "pending"

    def to_representation(self, instance):
        """Handles to_representation, using the declared parameters and returning the expected value or API response."""
        payload = super().to_representation(instance)
        payload["status"] = instance.approval_status_slug
        return payload


class RegisterSerializer(LocationValidationMixin, serializers.ModelSerializer):
    """Defines RegisterSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    password = serializers.CharField(write_only=True)
    name = serializers.CharField(write_only=True)
    role = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    farm_address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    farm_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    vehicle = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    wilaya_id = serializers.IntegerField(write_only=True, required=False)
    commune_id = serializers.IntegerField(write_only=True, required=False)
    max_load_kg = serializers.IntegerField(write_only=True, required=False, min_value=1)
    delivery_wilaya_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
    )

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = User
        fields = [
            "id",
            "email",
            "password",
            "role",
            "name",
            "phone_number",
            "phone",
            "farm_address",
            "farm_name",
            "vehicle",
            "address",
            "wilaya_id",
            "commune_id",
            "max_load_kg",
            "delivery_wilaya_ids",
        ]
        read_only_fields = ["id"]

    def validate_password(self, value):
        """Handles validate_password, using the declared parameters and returning the expected value or API response."""
        validate_password(value)
        return value

    def validate_name(self, value):
        """Handles validate_name, using the declared parameters and returning the expected value or API response."""
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Full name is required.")
        return cleaned

    def validate(self, attrs):
        """Handles validate, using the declared parameters and returning the expected value or API response."""
        role_slug = clean_text(attrs.get("role")).lower()
        role_code = User.role_from_slug(role_slug)

        phone_number = clean_text(attrs.get("phone_number"))
        phone_alias = clean_text(attrs.get("phone"))
        farm_address = clean_text(attrs.get("farm_address"))
        vehicle = clean_text(attrs.get("vehicle"))
        address = clean_text(attrs.get("address"))
        farm_name = clean_text(attrs.get("farm_name"))

        attrs["phone_number"] = phone_number or phone_alias
        attrs["phone"] = attrs["phone_number"]
        attrs["farm_address"] = farm_address
        attrs["vehicle"] = vehicle
        attrs["address"] = address
        attrs["farm_name"] = farm_name

        errors = {}
        role_label = role_slug.capitalize() or "Selected role"
        allowed_signup_roles = {"farmer", "buyer", "transporter"}

        if role_slug not in allowed_signup_roles or not role_code:
            errors["role"] = "Invalid signup role."

        if not attrs["phone_number"]:
            errors["phone_number"] = f"Phone number is required for {role_label} signup."
        elif not PHONE_REGEX.fullmatch(attrs["phone_number"]):
            errors["phone_number"] = "Enter a valid phone number."

        if role_slug == "farmer":
            if not farm_address:
                errors["farm_address"] = "Farm address is required for Farmer signup."
            elif Farm.objects.filter(location__iexact=farm_address).exists():
                errors["farm_address"] = (
                    "A farmer is already registered with this farm address. "
                    "Please use a different farm address."
                )

        if role_slug == "buyer" and not address:
            errors["address"] = "Address is required for Buyer signup."

        if role_slug == "transporter" and not vehicle:
            errors["vehicle"] = "Vehicle is required for Transporter signup."

        if errors:
            raise serializers.ValidationError(errors)

        if role_slug in {"farmer", "buyer"}:
            self._extract_location_pair(attrs, required=True)

        if role_slug == "transporter":
            max_load_kg = parse_int(attrs.get("max_load_kg"))
            if max_load_kg is None or max_load_kg <= 0:
                raise serializers.ValidationError(
                    {"max_load_kg": "Maximum load capacity in KG is required and must be greater than zero."}
                )
            attrs["max_load_kg"] = max_load_kg
            self._extract_delivery_wilayas(attrs, required=True)

        attrs["_role_code"] = role_code
        attrs["_role_slug"] = role_slug
        return attrs

    def create(self, validated_data):
        """Handles create, using the declared parameters and returning the expected value or API response."""
        name = validated_data.pop("name", "")
        first_name, _, last_name = name.strip().partition(" ")
        role_code = validated_data.pop("_role_code")
        role_slug = validated_data.pop("_role_slug")

        phone_number = validated_data.pop("phone_number", "")
        validated_data.pop("phone", None)
        farm_address = validated_data.pop("farm_address", "")
        farm_name = validated_data.pop("farm_name", "")
        vehicle = validated_data.pop("vehicle", "")
        address = validated_data.pop("address", "")
        password = validated_data.pop("password")
        email = validated_data["email"]
        wilaya = validated_data.pop("_wilaya", None)
        commune = validated_data.pop("_commune", None)
        delivery_wilayas = validated_data.pop("_delivery_wilayas", [])
        max_load_kg = validated_data.pop("max_load_kg", None)

        try:
            with transaction.atomic():
                user = User(
                    username=email,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=role_code,
                    status=User.Status.PENDING,
                    address=address if role_slug == "buyer" else "",
                    phone_number=phone_number,
                )
                user.set_password(password)
                user.save()

                if role_slug == "farmer":
                    farmer = Farmer.objects.create(person=user)
                    Farm.objects.create(
                        farmer=farmer,
                        name=farm_name or f"{first_name or 'Farmer'} Farm",
                        location=farm_address,
                        wilaya=wilaya,
                        commune=commune,
                    )
                elif role_slug == "transporter":
                    transporter = Transporter.objects.create(
                        person=user,
                        vehicle_type=vehicle,
                        max_load_kg=max_load_kg,
                        capacity=max_load_kg,
                        service_area=", ".join(item.name for item in delivery_wilayas),
                    )
                    if delivery_wilayas:
                        transporter.delivery_wilayas.set(delivery_wilayas)
                elif role_slug == "buyer":
                    Buyer.objects.create(person=user, wilaya=wilaya, commune=commune)

                JoinRequest.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    email=user.email,
                    phone_number=phone_number,
                    address=(
                        compose_structured_address(farm_address, commune, wilaya)
                        if role_slug == "farmer"
                        else compose_structured_address(address, commune, wilaya)
                    ),
                    requested_role=role_code,
                    status=JoinRequest.RequestStatus.PENDING,
                )
        except IntegrityError as exc:
            if role_slug == "farmer" and farm_address:
                raise serializers.ValidationError(
                    {
                        "farm_address": (
                            "A farmer is already registered with this farm address. "
                            "Please use a different farm address."
                        )
                    }
                ) from exc
            raise

        return user

    def to_representation(self, instance):
        """Handles to_representation, using the declared parameters and returning the expected value or API response."""
        return UserSerializer(instance, context=self.context).data


class UserTokenSerializer(TokenObtainPairSerializer):
    """Defines UserTokenSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    @classmethod
    def get_token(cls, user):
        """Handles get_token, using the declared parameters and returning the expected value or API response."""
        token = super().get_token(user)
        token["role"] = user.role_slug
        token["status"] = user.approval_status_slug
        return token

    def validate(self, attrs):
        """Handles validate, using the declared parameters and returning the expected value or API response."""
        data = super().validate(attrs)

        if self.user.status == User.Status.PENDING and self.user.role not in {
            User.Role.BUYER,
            User.Role.TRANSPORTER,
        }:
            raise AuthenticationFailed("Your account is waiting for ministry approval.")

        if self.user.status == User.Status.REJECTED:
            raise AuthenticationFailed(
                "Your account has been rejected by the ministry. Please contact support."
            )

        data["user"] = UserSerializer(self.user).data
        return data


class UserApprovalUpdateSerializer(serializers.ModelSerializer):
    """Defines UserApprovalUpdateSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    approval_status = serializers.ChoiceField(choices=["pending", "approved", "rejected"])

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        model = User
        fields = ["approval_status"]

    def update(self, instance, validated_data):
        """Handles update, using the declared parameters and returning the expected value or API response."""
        approval_slug = validated_data["approval_status"]
        new_status = User.status_from_slug(approval_slug)
        instance.status = new_status
        instance.save(update_fields=["status"])
        return instance


class FarmerAccountSerializer(LocationValidationMixin, serializers.Serializer):
    """Defines FarmerAccountSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    name = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    farmAddress = serializers.CharField(required=False, allow_blank=True)
    farm_address = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    contactInfo = serializers.CharField(required=False, allow_blank=True)
    contact_info = serializers.CharField(required=False, allow_blank=True)
    wilaya_id = serializers.IntegerField(required=False)
    commune_id = serializers.IntegerField(required=False)

    def to_representation(self, user):
        """Handles to_representation, using the declared parameters and returning the expected value or API response."""
        farmer = user.farmer
        farm = primary_farm(farmer)
        return {
            "name": farm.name if farm else "",
            "location": farm.location if farm else "",
            "description": user.documents_url,
            "contactInfo": user.phone_number,
            "farmAddress": farm.location if farm else "",
            "farm_address": farm.location if farm else "",
            "wilaya_id": farm.wilaya_id if farm else None,
            "wilayaId": farm.wilaya_id if farm else None,
            "wilaya_name": farm.wilaya.name if farm and farm.wilaya else "",
            "commune_id": farm.commune_id if farm else None,
            "communeId": farm.commune_id if farm else None,
            "commune_name": farm.commune.name if farm and farm.commune else "",
            "location_label": farm.location_label if farm else "",
        }

    def validate(self, attrs):
        """Handles validate, using the declared parameters and returning the expected value or API response."""
        self._extract_location_pair(attrs, required=True)

        farm_address = clean_text(attrs.get("farmAddress") or attrs.get("farm_address") or attrs.get("location"))
        if not farm_address:
            raise serializers.ValidationError({"farmAddress": "Farm address is required."})

        attrs["farmAddress"] = farm_address
        attrs["location"] = farm_address
        attrs["description"] = clean_text(attrs.get("description"))
        attrs["contactInfo"] = clean_text(attrs.get("contactInfo") or attrs.get("contact_info"))
        attrs["name"] = clean_text(attrs.get("name"))
        return attrs

    def update(self, user, validated_data):
        """Handles update, using the declared parameters and returning the expected value or API response."""
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

        user.documents_url = validated_data["description"]
        user.phone_number = validated_data["contactInfo"]
        user.save(update_fields=["documents_url", "phone_number"])

        farm.name = validated_data["name"] or farm.name
        farm.location = validated_data["farmAddress"]
        farm.wilaya = validated_data["_wilaya"]
        farm.commune = validated_data["_commune"]
        farm.save(update_fields=["name", "location", "wilaya", "commune"])
        return user


class BuyerAccountSerializer(LocationValidationMixin, serializers.Serializer):
    """Defines BuyerAccountSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    address = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    wilaya_id = serializers.IntegerField(required=False)
    commune_id = serializers.IntegerField(required=False)

    def to_representation(self, user):
        """Handles to_representation, using the declared parameters and returning the expected value or API response."""
        buyer = user.buyer
        return {
            "address": compose_structured_address(user.address, buyer.commune, buyer.wilaya),
            "street_address": user.address,
            "phone_number": user.phone_number,
            "phone": user.phone_number,
            "wilaya_id": buyer.wilaya_id,
            "wilayaId": buyer.wilaya_id,
            "wilaya_name": buyer.wilaya.name if buyer.wilaya else "",
            "commune_id": buyer.commune_id,
            "communeId": buyer.commune_id,
            "commune_name": buyer.commune.name if buyer.commune else "",
            "location_label": buyer.location_label,
        }

    def validate(self, attrs):
        """Handles validate, using the declared parameters and returning the expected value or API response."""
        self._extract_location_pair(attrs, required=True)
        address = clean_text(attrs.get("address"))
        phone_number = clean_text(attrs.get("phone_number") or attrs.get("phone"))

        errors = {}
        if not address:
            errors["address"] = "Address is required."
        if not phone_number:
            errors["phone_number"] = "Phone number is required."
        elif not PHONE_REGEX.fullmatch(phone_number):
            errors["phone_number"] = "Enter a valid phone number."

        if errors:
            raise serializers.ValidationError(errors)

        attrs["address"] = address
        attrs["phone_number"] = phone_number
        return attrs

    def update(self, user, validated_data):
        """Handles update, using the declared parameters and returning the expected value or API response."""
        buyer = getattr(user, "buyer", None)
        if not buyer:
            buyer = Buyer.objects.create(person=user)

        user.address = validated_data["address"]
        user.phone_number = validated_data["phone_number"]
        user.save(update_fields=["address", "phone_number"])

        buyer.wilaya = validated_data["_wilaya"]
        buyer.commune = validated_data["_commune"]
        buyer.save(update_fields=["wilaya", "commune"])
        return user


class TransporterAccountSerializer(LocationValidationMixin, serializers.Serializer):
    """Defines TransporterAccountSerializer for this app and is used by the serializers, views, routes, or admin when imported."""
    vehicle = serializers.CharField(required=False, allow_blank=True)
    max_load_kg = serializers.IntegerField(required=False)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    delivery_wilaya_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
    )

    def to_representation(self, user):
        """Handles to_representation, using the declared parameters and returning the expected value or API response."""
        transporter = user.transporter
        delivery_wilayas = list(transporter.delivery_wilayas.order_by("id"))
        return {
            "vehicle": transporter.vehicle_type,
            "max_load_kg": transporter.max_load_kg,
            "capacity": transporter.capacity,
            "phone_number": user.phone_number,
            "phone": user.phone_number,
            "service_area": transporter.service_area,
            "delivery_wilaya_ids": [wilaya.id for wilaya in delivery_wilayas],
            "deliveryWilayaIds": [wilaya.id for wilaya in delivery_wilayas],
            "delivery_wilayas": [
                {"id": wilaya.id, "code": wilaya.code, "name": wilaya.name} for wilaya in delivery_wilayas
            ],
        }

    def validate(self, attrs):
        """Handles validate, using the declared parameters and returning the expected value or API response."""
        vehicle = clean_text(attrs.get("vehicle"))
        phone_number = clean_text(attrs.get("phone_number") or attrs.get("phone"))
        max_load_kg = parse_int(attrs.get("max_load_kg"))

        self._extract_delivery_wilayas(attrs, required=True)

        errors = {}
        if not vehicle:
            errors["vehicle"] = "Vehicle type is required."
        if not phone_number:
            errors["phone_number"] = "Phone number is required."
        elif not PHONE_REGEX.fullmatch(phone_number):
            errors["phone_number"] = "Enter a valid phone number."
        if max_load_kg is None or max_load_kg <= 0:
            errors["max_load_kg"] = "Maximum load capacity in KG is required and must be greater than zero."

        if errors:
            raise serializers.ValidationError(errors)

        attrs["vehicle"] = vehicle
        attrs["phone_number"] = phone_number
        attrs["max_load_kg"] = max_load_kg
        return attrs

    def update(self, user, validated_data):
        """Handles update, using the declared parameters and returning the expected value or API response."""
        transporter = getattr(user, "transporter", None)
        if not transporter:
            transporter = Transporter.objects.create(person=user)

        user.phone_number = validated_data["phone_number"]
        user.save(update_fields=["phone_number"])

        transporter.vehicle_type = validated_data["vehicle"]
        transporter.max_load_kg = validated_data["max_load_kg"]
        transporter.capacity = validated_data["max_load_kg"]
        transporter.service_area = ", ".join(item.name for item in validated_data["_delivery_wilayas"])
        transporter.save(update_fields=["vehicle_type", "max_load_kg", "capacity", "service_area"])
        transporter.delivery_wilayas.set(validated_data["_delivery_wilayas"])
        return user
