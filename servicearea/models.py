import uuid
from django.contrib.gis.db import models


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
