import json

from django import forms
from django.contrib import admin
from django.contrib.gis.geos import Polygon


from servicearea.models import ServiceArea


class ServiceAreaAdminForm(forms.ModelForm):
    polygon = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 8}),
        help_text="""
Enter coordinates as JSON.

Example:

[
    [3.379206, 6.524379],
    [3.380000, 6.530000],
    [3.385000, 6.528000]
]

Coordinates are in GeoJSON order:
[longitude, latitude]
""",
    )

    class Meta:
        model = ServiceArea
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk and self.instance.polygon:
            # Remove the duplicated closing coordinate
            coords = [[lon, lat] for lon, lat in self.instance.polygon.coords[0][:-1]]

            self.initial["polygon"] = json.dumps(coords, indent=4)

    def clean_polygon(self):
        raw = self.cleaned_data["polygon"]

        try:
            coords = json.loads(raw)
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON.")

        if not isinstance(coords, list):
            raise forms.ValidationError("Polygon must be a list of coordinates.")

        if len(coords) < 3:
            raise forms.ValidationError(
                "A polygon must contain at least 3 coordinate pairs."
            )

        ring = []

        for point in coords:
            if not isinstance(point, list) or len(point) != 2:
                raise forms.ValidationError(
                    "Each coordinate must be [longitude, latitude]."
                )

            lon, lat = point

            try:
                lon = float(lon)
                lat = float(lat)
            except (TypeError, ValueError):
                raise forms.ValidationError("Longitude and latitude must be numbers.")

            ring.append((lon, lat))

        # Close the polygon automatically
        if ring[0] != ring[-1]:
            ring.append(ring[0])

        # return Polygon(ring, srid=4326)
        return Polygon(ring)


@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    form = ServiceAreaAdminForm

    list_display = (
        "name",
        "responder_count",
        "created_at",
    )

    search_fields = ("name",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Responders")
    def responder_count(self, obj):
        return obj.first_responders.count()
