"""
File responsibility: Defines database tables and relationships for this Django app.
Connects to the Django backend through imports, app configuration, API routing, or management commands.
"""

# Imports: load Django, DRF, models, serializers, and helpers used in this module.
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    """Defines UserManager for this app and is used by the serializers, views, routes, or admin when imported."""
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Handles _create_user, using the declared parameters and returning the expected value or API response."""
        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Handles create_user, using the declared parameters and returning the expected value or API response."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Handles create_superuser, using the declared parameters and returning the expected value or API response."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.MINISTRY)
        extra_fields.setdefault("status", User.Status.APPROVED)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Defines User for this app and is used by the serializers, views, routes, or admin when imported."""
    class Role(models.IntegerChoices):
        """Defines Role for this app and is used by the serializers, views, routes, or admin when imported."""
        FARMER = 1, "Farmer"
        BUYER = 2, "Buyer"
        TRANSPORTER = 3, "Transporter"
        MINISTRY = 4, "Ministry"

    class Status(models.IntegerChoices):
        """Defines Status for this app and is used by the serializers, views, routes, or admin when imported."""
        PENDING = 0, "Pending Approval"
        APPROVED = 1, "Approved"
        REJECTED = 2, "Rejected"

    ROLE_SLUGS = {
        Role.FARMER: "farmer",
        Role.BUYER: "buyer",
        Role.TRANSPORTER: "transporter",
        Role.MINISTRY: "ministry",
    }

    STATUS_SLUGS = {
        Status.PENDING: "pending",
        Status.APPROVED: "approved",
        Status.REJECTED: "rejected",
    }

    id = models.AutoField(primary_key=True, db_column="IDPerson")
    first_name = models.CharField(max_length=100, blank=True, db_column="FirstName")
    last_name = models.CharField(max_length=100, blank=True, db_column="LastName")
    address = models.CharField(max_length=255, blank=True, db_column="Address")
    phone_number = models.CharField(max_length=30, blank=True, db_column="PhoneNumber")
    personal_picture_url = models.CharField(max_length=255, blank=True, db_column="personalPictureURL")
    documents_url = models.CharField(max_length=255, blank=True, db_column="DocumentsURL")
    email = models.EmailField(unique=True, db_column="Email")
    username = models.CharField(max_length=100, unique=True, db_column="Username")
    password = models.CharField(max_length=255, db_column="Password")
    status = models.PositiveSmallIntegerField(
        choices=Status.choices,
        default=Status.PENDING,
        db_column="Status",
        db_index=True,
    )
    role = models.PositiveSmallIntegerField(
        choices=Role.choices,
        default=Role.FARMER,
        db_column="Role",
        db_index=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Person"
        verbose_name = "person"
        verbose_name_plural = "people"

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return f"{self.email} ({self.get_role_display()})"

    @property
    def role_slug(self):
        """Handles role_slug, using the declared parameters and returning the expected value or API response."""
        return self.ROLE_SLUGS.get(self.role, "unknown")

    @property
    def approval_status_slug(self):
        """Handles approval_status_slug, using the declared parameters and returning the expected value or API response."""
        return self.STATUS_SLUGS.get(self.status, "pending")

    @classmethod
    def role_from_slug(cls, value):
        """Handles role_from_slug, using the declared parameters and returning the expected value or API response."""
        mapping = {
            "farmer": cls.Role.FARMER,
            "buyer": cls.Role.BUYER,
            "transporter": cls.Role.TRANSPORTER,
            "ministry": cls.Role.MINISTRY,
        }
        return mapping.get((value or "").strip().lower())

    @classmethod
    def status_from_slug(cls, value):
        """Handles status_from_slug, using the declared parameters and returning the expected value or API response."""
        mapping = {
            "pending": cls.Status.PENDING,
            "approved": cls.Status.APPROVED,
            "rejected": cls.Status.REJECTED,
        }
        return mapping.get((value or "").strip().lower())


class Farmer(models.Model):
    """Defines Farmer for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDFarmer")
    person = models.OneToOneField(User, on_delete=models.CASCADE, db_column="IDPerson", related_name="farmer")
    average_rating = models.IntegerField(null=True, blank=True, db_column="AverageRating")
    total_reviews = models.IntegerField(null=True, blank=True, db_column="TotalReviews")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Farmer"

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return f"Farmer<{self.person.email}>"


class Buyer(models.Model):
    """Defines Buyer for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDBuyer")
    person = models.OneToOneField(User, on_delete=models.CASCADE, db_column="IDPerson", related_name="buyer")
    wilaya = models.ForeignKey(
        "locations.Wilaya",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="IDWilaya",
        related_name="buyers",
    )
    commune = models.ForeignKey(
        "locations.Commune",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="IDCommune",
        related_name="buyers",
    )

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Buyer"

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return f"Buyer<{self.person.email}>"

    @property
    def location_label(self):
        """Handles location_label, using the declared parameters and returning the expected value or API response."""
        if self.commune and self.wilaya:
            return f"{self.commune.name}, {self.wilaya.name}"
        if self.wilaya:
            return self.wilaya.name
        return self.person.address


class AdminProfile(models.Model):
    """Defines AdminProfile for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDAdmin")
    person = models.OneToOneField(User, on_delete=models.CASCADE, db_column="IDPerson", related_name="admin_profile")
    total_processes = models.IntegerField(default=0, db_column="TotalProcesses")
    region_code = models.IntegerField(null=True, blank=True, db_column="RegionCode")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Admin"

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return f"Admin<{self.person.email}>"


class Transporter(models.Model):
    """Defines Transporter for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDTransporter")
    person = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        db_column="IDPerson",
        related_name="transporter",
    )
    capacity = models.IntegerField(null=True, blank=True, db_column="Capacity")
    service_area = models.CharField(max_length=255, blank=True, db_column="ServiceArea")
    vehicle_type = models.CharField(max_length=100, blank=True, db_column="VehicleType")
    max_load_kg = models.PositiveIntegerField(null=True, blank=True, db_column="MaxLoadKg")
    delivery_wilayas = models.ManyToManyField(
        "locations.Wilaya",
        related_name="transporters",
        blank=True,
        db_table="TransporterDeliveryWilaya",
    )
    average_rating = models.IntegerField(null=True, blank=True, db_column="AverageRating")
    total_reviews = models.IntegerField(null=True, blank=True, db_column="TotalReviews")

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Transporter"

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return f"Transporter<{self.person.email}>"

    @property
    def coverage_label(self):
        """Handles coverage_label, using the declared parameters and returning the expected value or API response."""
        wilayas = list(self.delivery_wilayas.order_by("id").values_list("name", flat=True))
        return ", ".join(wilayas) if wilayas else self.service_area


class Farm(models.Model):
    """Defines Farm for this app and is used by the serializers, views, routes, or admin when imported."""
    id = models.AutoField(primary_key=True, db_column="IDFarm")
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, db_column="IDFarmer", related_name="farms")
    location = models.CharField(max_length=255, db_column="Location")
    name = models.CharField(max_length=150, blank=True, db_column="Name")
    area = models.IntegerField(null=True, blank=True, db_column="Area")
    wilaya = models.ForeignKey(
        "locations.Wilaya",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="IDWilaya",
        related_name="farms",
    )
    commune = models.ForeignKey(
        "locations.Commune",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        db_column="IDCommune",
        related_name="farms",
    )

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "Farm"
        constraints = [
            models.UniqueConstraint(Lower("location"), name="unique_farm_location_ci"),
        ]

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return self.name or self.location

    @property
    def location_label(self):
        """Handles location_label, using the declared parameters and returning the expected value or API response."""
        if self.commune and self.wilaya:
            return f"{self.commune.name}, {self.wilaya.name}"
        if self.wilaya:
            return self.wilaya.name
        return self.location


class JoinRequest(models.Model):
    """Defines JoinRequest for this app and is used by the serializers, views, routes, or admin when imported."""
    class RequestStatus(models.IntegerChoices):
        """Defines RequestStatus for this app and is used by the serializers, views, routes, or admin when imported."""
        PENDING = 0, "Pending"
        APPROVED = 1, "Approved"
        REJECTED = 2, "Rejected"

    id = models.AutoField(primary_key=True, db_column="IDRequest")
    admin = models.ForeignKey(
        AdminProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column="IDAdmin",
        related_name="join_requests",
    )
    first_name = models.CharField(max_length=100, blank=True, db_column="FirstName")
    last_name = models.CharField(max_length=100, blank=True, db_column="LastName")
    email = models.EmailField(max_length=150, db_column="Email")
    phone_number = models.CharField(max_length=30, blank=True, db_column="PhoneNumber")
    address = models.CharField(max_length=255, blank=True, db_column="Address")
    requested_role = models.PositiveSmallIntegerField(db_column="RequestedRole")
    personal_picture_url = models.CharField(max_length=255, blank=True, db_column="personalPictureURL")
    documents_url = models.CharField(max_length=255, blank=True, db_column="DocumentsURL")
    request_date = models.DateTimeField(auto_now_add=True, db_column="RequestDate")
    review_date = models.DateTimeField(null=True, blank=True, db_column="ReviewDate")
    notes = models.CharField(max_length=255, blank=True, db_column="Notes")
    status = models.PositiveSmallIntegerField(
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        db_column="Status",
        db_index=True,
    )

    class Meta:
        """Defines Meta for this app and is used by the serializers, views, routes, or admin when imported."""
        db_table = "JoinRequest"

    def __str__(self):
        """Handles __str__, using the declared parameters and returning the expected value or API response."""
        return f"JoinRequest<{self.email}>"
