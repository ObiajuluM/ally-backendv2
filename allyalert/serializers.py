from rest_framework import serializers
from rest_framework_gis.fields import GeometryField

from allyalert.models import AllyAlert, AlertDelivery, AlertReport


class AllyAlertSerializer(serializers.ModelSerializer):
    # GeoJSON geometry fields — accept/return {"type": "Point", "coordinates": [lng, lat]}
    # required=False + allow_null=True mirrors the null=True, blank=True on the model fields.
    created_location = GeometryField(required=False, allow_null=True)
    target_location = GeometryField(required=False, allow_null=True)

    # Expose creator as read-only ID; the view sets it from request.user.
    creator = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AllyAlert
        fields = [
            "id",
            "creator",
            "title",
            "description",
            "created_location",
            "target_location",
            "radius_km",
            "expires_at",
            "status",
            "helpful_count",
            "report_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "helpful_count",
            "report_count",
            "created_at",
            "updated_at",
        ]


class AlertDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertDelivery
        fields = [
            "id",
            "alert",
            "user",
            "delivered_at",
            "viewed_at",
        ]
        read_only_fields = ["id", "delivered_at", "alert", "user"]


class AlertReportSerializer(serializers.ModelSerializer):
    # Reporter is set from request.user in the view, not supplied by the client.
    reporter = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = AlertReport
        fields = [
            "id",
            "alert",
            "reporter",
            "reason",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "reporter", "created_at"]
