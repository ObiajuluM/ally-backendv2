import uuid
from django.contrib.gis.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from ally.models import Address


# Create your models here.
class ServiceArea(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=255, blank=True, null=True, help_text="e.g. Lagos Mainland Zone 1"
    )

    # Each ServiceArea is a single polygon for easier spatial lookups
    polygon = models.PolygonField(
        blank=False,
        null=False,
        spatial_index=True,
        help_text="Spatial boundary of this specific coverage zone.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or f"Service Area {self.id}"


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


# TODO: Make searchable
# Tags related to types of crises or intervention
class FirstResponderTag(models.TextChoices):
    ABUSE = "abuse"
    ACCIDENT = "accident"
    ARMEDROBBERY = "armedrobbery"
    ARMY = "army"
    ATTACK = "attack"
    BEATING = "beating"
    CULT = "cult"
    DISASTER = "disaster"
    DOMESTICVIOLENCE = "domesticviolence"
    DRUG = "drug"
    ENFORCEMENT = "enforcement"
    FIGHT = "fight"
    FIRE = "fire"
    FIRESERVICE = "fireservice"
    FLOOD = "flood"
    FOOD = "food"
    GENERAL = "general"
    GOVERNMENT = "government"
    GUN = "gun"
    HARASSMENT = "harassment"
    HEALTH = "health"
    HELP = "help"
    HIGHWAYWAY = "highwayway"
    HOSPITAL = "hospital"
    KIDNAPPING = "kidnapping"
    LAW = "law"
    LAWENFORCEMENT = "lawenforcement"
    MILITARY = "military"
    MILITARYBRUTALITY = "militarybrutality"
    POLICE = "police"
    POLICEBRUTALITY = "policebrutality"
    POLICEHARASSMENT = "policeharassment"
    PUBLICGOOD = "publicgood"
    ROADSAFETY = "roadsafety"
    SAFETY = "safety"
    TERROR = "terror"
    TRAFFICKING = "trafficking"
    VIOLENCE = "violence"


# TODO: add trust rating
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

    # one FirstResponder can be assigned to many ServiceAreas, and conversely, one ServiceArea can have many FirstResponders assigned to it.
    service_areas = models.ManyToManyField(
        ServiceArea,
        blank=True,
        related_name="first_responders",
        help_text="The coverage zones assigned to this responder.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # ordering = ["-created_at"]
        # db_table = "ally_firstresponder"
        pass

    def __str__(self):
        return self.name or "Unnamed First Responder"


# When a FirstResponder is deleted, also delete their linked Address.
@receiver(post_delete, sender=FirstResponder)
def delete_address_on_first_responder_delete(sender, instance, **kwargs):
    if instance.address_id:
        Address.objects.filter(pk=instance.address_id).delete()
