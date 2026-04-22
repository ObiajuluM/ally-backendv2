from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_delete
from django.dispatch import receiver
import uuid
from geopy.geocoders import Nominatim


#
class FirstResponderType(models.TextChoices):
    FIRSTAIDANDMEDICAL = "firstaidandmedical"
    ABUSEANDVIOLENCE = "abuseandviolence"
    ACCIDENTSANDDISASTER = "accidentsanddisaster"
    LAWENFORCEMENT = "lawenforcement"


# Organization category
class OrganizationType(models.TextChoices):
    GOVERNMENT = "government"
    NGO = "ngo"
    PRIVATE = "private"
    COMMUNITY = "community"


# Tags related to types of crises or intervention
class FirstResponderTag(models.TextChoices):
    GENERAL = "general"
    POLICE = "police"
    MILITARY = "military"
    ROADSAFETY = "roadsafety"
    FIRESERVICE = "fireservice"
    LAWENFORCEMENT = "lawenforcement"
    HOSPITAL = "hospital"
    GOVERNMENT = "government"
    ABUSE = "abuse"
    DRUG = "drug"
    FOOD = "food"
    HEALTH = "health"
    TRAFFICKING = "trafficking"
    LAW = "law"
    ENFORCEMENT = "enforcement"
    SAFETY = "safety"
    ARMEDROBBERY = "armedrobbery"
    HIGHWAYWAY = "highwayway"
    HARASSMENT = "harassment"
    POLICEHARASSMENT = "policeharassment"
    POLICEBRUTALITY = "policebrutality"
    DOMESTICVIOLENCE = "domesticviolence"
    FIGHT = "fight"
    ARMY = "army"
    MILITARYBRUTALITY = "militarybrutality"
    VIOLENCE = "violence"
    BEATING = "beating"
    ACCIDENT = "accident"
    DISASTER = "disaster"
    PUBLICGOOD = "publicgood"
    FIRE = "fire"
    FLOOD = "flood"
    KIDNAPPING = "kidnapping"
    GUN = "gun"
    TERROR = "terror"
    HELP = "help"
    CULT = "cult"
    ATTACK = "attack"


class Address(models.Model):
    latitude = models.DecimalField(
        blank=True,
        null=True,
        help_text="Latitude of location",
        max_digits=9,
        decimal_places=6,
    )
    longitude = models.DecimalField(
        blank=True,
        null=True,
        help_text="Longitude of location",
        max_digits=9,
        decimal_places=6,
    )
    full_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Full address (e.g., Lagos, Nigeria)",
    )

    def __address_from_latlong(self):
        print("Running reverse geocoding for address...")
        # Initialize Nominatim API
        geolocator = Nominatim(user_agent="ally")
        if self.latitude is not None and self.longitude is not None:
            try:
                location = geolocator.reverse(
                    (self.latitude, self.longitude),
                )
                if location and location.address:
                    self.full_address = location.address
            except Exception as e:
                # Log the error or handle it as needed
                print(f"Error during reverse geocoding: {e}")
        pass

    def save(self, *args, **kwargs):
        # Run the reverse-geocode helper every time this record is saved.
        self.__address_from_latlong()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{ self.latitude} {self.longitude} {self.full_address}"


class FirstResponder(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Organization or individual name",
    )

    # Primary responder type used for high-level classification.
    firstresponder_type = models.CharField(
        max_length=32,
        choices=FirstResponderType.choices,
        blank=True,
        null=True,
    )

    organization_type = models.CharField(
        max_length=20,
        choices=OrganizationType.choices,
        blank=True,
        null=True,
    )

    description = models.TextField(
        blank=True,
        null=True,
        max_length=255,
    )

    phones = models.JSONField(
        blank=True,
        null=True,
        help_text="List of phone numbers as strings (e.g., ['+1234567890', '+0987654321'])",
        default=list,
    )

    availability = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Availability e.g. '24/7'",
    )

    socials = models.JSONField(
        blank=True,
        null=True,
        help_text="dict of social media links (e.g., {'facebook': 'https://facebook.com/firstresponder', 'twitter': 'https://twitter.com/firstresponder', website: 'https://firstresponder.org'})",
        default=dict,
    )

    response_time = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Average response time (e.g., '5 mins')",
    )

    # Foreign key to location
    address = models.OneToOneField(
        Address,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    # Tags for search and classification
    tags = models.JSONField(
        blank=True,
        null=True,
        help_text="List of FirstResponderTag values",
        default=list,
    )

    metadata = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text='Additional metadata as JSON (e.g., {"key": "value"})',
    )

    # Each entry is a polygon: a list of [lat, lng] pairs.
    # A responder can cover multiple disconnected regions.
    # e.g. [[[5.3,7.1],[5.3,8.0],[6.9,8.0],[6.9,7.1]], [[4.0,6.0],[4.0,7.0],[5.0,7.0],[5.0,6.0]]]
    service_areas = models.JSONField(
        blank=True,
        null=True,
        default=None,
        help_text="List of polygons, each a list of [lat, lng] pairs defining a service area.",
    )

    def __str__(self):
        return self.name or "Unnamed First Responder"


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

    USERNAME_FIELD = "email"  # Set email as the unique identifier for authentication
    REQUIRED_FIELDS = [
        "username"
    ]  # Required when creating a superuser, but not used for authentication

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


# When a FirstResponder is deleted, also delete their linked Address.
@receiver(post_delete, sender=FirstResponder)
def delete_address_on_first_responder_delete(sender, instance, **kwargs):
    if instance.address_id:
        Address.objects.filter(pk=instance.address_id).delete()
