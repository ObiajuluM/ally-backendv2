from django.contrib import admin

from allyalert.models import AlertDelivery, AlertReport, AllyAlert

from django.contrib.gis.geos import Point
from django.urls import reverse
from django.utils.html import format_html


@admin.register(AllyAlert)
class AllyAlertAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "creator",
        "status",
        "radius_km",
        "expires_at",
        # "created_location_display",
        # "target_location_display",
        "google_map",
        "delivery_count",
        "helpful_total",
        "report_total",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
        "expires_at",
    )

    search_fields = (
        "title",
        "description",
        "creator__email",
        "creator__username",
    )

    autocomplete_fields = ("creator",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "google_map",
    )

    fieldsets = (
        (
            "Alert",
            {
                "fields": (
                    "id",
                    "creator",
                    "title",
                    "description",
                    "status",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "created_location",
                    "target_location",
                    "radius_km",
                    "google_map",
                )
            },
        ),
        (
            "Timing",
            {
                "fields": (
                    "expires_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Engagement",
            {
                "fields": (
                    # TODO: make this show as an integer and link to the deliveries, helpfuls, and reports in the admin.
                    "helpful_count",
                    "report_count",
                    # "helpful_total",
                    # "report_total",
                )
            },
        ),
    )

    @admin.display(description="Created At")
    def created_location_display(self, obj):
        if not obj.created_location:
            return "-"

        return f"{obj.created_location.y:.6f}, {obj.created_location.x:.6f}"

    @admin.display(description="Target")
    def target_location_display(self, obj):
        if not obj.target_location:
            return "-"

        return f"{obj.target_location.y:.6f}, {obj.target_location.x:.6f}"

    @admin.display(description="Map that points to target location")
    def google_map(self, obj):
        if not obj.target_location:
            return "-"

        lat = obj.target_location.y
        lon = obj.target_location.x

        return format_html(
            '<a href="https://www.google.com/maps?q={},{}" target="_blank">'
            "Open Google Maps"
            "</a>",
            lat,
            lon,
        )

    @admin.display(description="Deliveries")
    def delivery_count(self, obj):
        return obj.deliveries.count()

    @admin.display(description="Helpful")
    def helpful_total(self, obj):
        return len(obj.helpful_count)

    @admin.display(description="Reports")
    def report_total(self, obj):
        return len(obj.report_count)


@admin.register(AlertDelivery)
class AlertDeliveryAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "alert_title",
        "user",
        "delivered_at",
        "viewed_at",
        "is_viewed",
    )

    list_filter = (
        "viewed_at",
        "delivered_at",
    )

    search_fields = (
        "user__email",
        "user__username",
        "alert__title",
    )

    autocomplete_fields = (
        "user",
        "alert",
    )

    readonly_fields = (
        "id",
        "delivered_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "id",
                    "alert",
                    "user",
                )
            },
        ),
        (
            "Delivery",
            {
                "fields": (
                    "delivered_at",
                    "viewed_at",
                )
            },
        ),
    )

    @admin.display(description="Alert")
    def alert_title(self, obj):
        url = reverse(
            "admin:allyalert_allyalert_change",
            args=[obj.alert.pk],
        )

        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.alert.title,
        )

    @admin.display(boolean=True, description="Viewed")
    def is_viewed(self, obj):
        return obj.viewed_at is not None


@admin.register(AlertReport)
class AlertReportAdmin(admin.ModelAdmin):
    pass
