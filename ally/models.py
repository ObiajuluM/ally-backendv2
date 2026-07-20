from django.contrib.gis.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_delete
from django.dispatch import receiver
import uuid
from geopy.geocoders import Nominatim


class Address(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    location = models.PointField(
        # geography=True,
        spatial_index=True,
        null=True,
        blank=True,
    )
    as_string = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Full address (e.g., Lagos, Nigeria)",
    )

    @property
    def longitude(self):
        # Fixed: Changed self.point to self.location
        return self.location.x if self.location else None

    @property
    def latitude(self):
        # Fixed: Changed self.point to self.location
        return self.location.y if self.location else None

    def __address_from_longlat(self):
        print("Running reverse geocoding for address...")

        # Initialize Nominatim API
        geolocator = Nominatim(user_agent="ally")

        # Check if coordinates exist using your properties
        if self.latitude is not None and self.longitude is not None:
            try:
                # Fixed: Use your model's properties (self.latitude, self.longitude)
                addr = geolocator.reverse((self.latitude, self.longitude))
                if addr and addr.address:
                    self.as_string = addr.address
            except Exception as e:
                print(f"Error during reverse geocoding: {e}")

    def save(self, *args, **kwargs):
        # Run the reverse-geocode helper every time this record is saved.
        # if not self.as_string:
        self.__address_from_longlat()
        super().save(*args, **kwargs)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # class Meta:
    #     ordering = ["-created_at"]

    def __str__(self):
        return f"{self.longitude} - {self.latitude}, {self.as_string}"


class MyInformation(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255, null=True, blank=True)

    birthday = models.DateField(null=True, blank=True)
    address = models.OneToOneField(
        Address,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    gender = models.CharField(max_length=50, null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    allergies = models.JSONField(
        null=True,
        blank=True,
        default=list,
        help_text="List of allergies",
    )
    medications = models.JSONField(
        null=True,
        blank=True,
        default=list,
        help_text="List of medications",
    )
    medical_notes = models.TextField(null=True, blank=True)
    organ_donor = models.BooleanField(default=False)
    is_pregnant = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    trusted_contacts = models.JSONField(
        null=True,
        blank=True,
        default=list,
        help_text="List of trusted contacts (e.g., [{'name': 'John Doe', 'phone': '+1234567890'}])",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # db_table = "ally_myinformation"
        pass

    def __str__(self):
        return self.name or "My information"


# Create your models here.
class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    my_information = models.OneToOneField(
        MyInformation, on_delete=models.CASCADE, null=True, blank=True
    )
    location = models.PointField(
        # geography=True,
        spatial_index=True,
        null=True,
        blank=True,
        help_text="user's last seen location",
    )
    is_streaming = models.BooleanField(
        default=False, help_text="Is the user currently streaming their location?"
    )

    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"  # Set email as the unique identifier for authentication
    REQUIRED_FIELDS = [
        "username"
    ]  # Required when creating a superuser, but not used for authentication

    # class Meta(AbstractUser.Meta):
    #     ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.username} --- {self.email}"


# When a User is deleted, also delete their linked MyInformation.
# This is necessary because the FK lives on User, so Django's built-in
# CASCADE only protects the reverse direction (MyInformation → User).
@receiver(post_delete, sender=User)
def delete_my_information_on_user_delete(sender, instance, **kwargs):
    if instance.my_information_id:
        MyInformation.objects.filter(pk=instance.my_information_id).delete()


# When a MyInformation row is deleted (e.g. triggered by the signal above),
# also delete the linked Address row.
@receiver(post_delete, sender=MyInformation)
def delete_address_on_my_information_delete(sender, instance, **kwargs):
    if instance.address_id:
        Address.objects.filter(pk=instance.address_id).delete()
