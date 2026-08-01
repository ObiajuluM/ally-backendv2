from rest_framework import serializers
from rest_framework_gis.fields import GeometryField
from django.contrib.gis.geos import Point

from allyalert.models import AllyAlert, AlertDelivery, AlertReport


class AllyAlertSerializer(serializers.ModelSerializer):
    # GeoJSON geometry fields — accept/return {"type": "Point", "coordinates": [lng, lat]}
    # required=False + allow_null=True mirrors the null=True, blank=True on the model fields.
    # created_location = GeometryField(required=False, allow_null=True)
    # target_location = GeometryField(required=False, allow_null=True)

    created_location_latitude = serializers.FloatField(required=False, allow_null=True)
    created_location_longitude = serializers.FloatField(required=False, allow_null=True)

    target_location_latitude = serializers.FloatField(required=False, allow_null=True)
    target_location_longitude = serializers.FloatField(required=False, allow_null=True)

    # Expose creator as read-only ID; the view sets it from request.user.
    creator = serializers.PrimaryKeyRelatedField(read_only=True)

    #
    def to_representation(self, instance):
        """Controls what data is sent OUT to the API client."""
        representation = super().to_representation(instance)
        #
        representation["created_location_longitude"] = (
            instance.created_location_longitude
        )
        representation["created_location_latitude"] = instance.created_location_latitude

        #
        representation["target_location_longitude"] = instance.target_location_longitude
        representation["target_location_latitude"] = instance.target_location_latitude
        return representation

    def validate(self, attrs):
        """Validates coordinates and packages them into Point objects."""
        created_lat = attrs.pop("created_location_latitude", None)
        created_lon = attrs.pop("created_location_longitude", None)

        target_lat = attrs.pop("target_location_latitude", None)
        target_lon = attrs.pop("target_location_longitude", None)

        # Ensure both coordinates are present if one is provided
        if (created_lat is not None and created_lon is None) or (
            created_lon is not None and created_lat is None
        ):
            raise serializers.ValidationError(
                "Both created_location latitude and longitude must be provided together."
            )

        if (target_lat is not None and target_lon is None) or (
            target_lon is not None and target_lat is None
        ):
            raise serializers.ValidationError(
                "Both target_location latitude and longitude must be provided together."
            )

        # Package coordinates into GeoDjango Point (X/Longitude first, Y/Latitude second)
        if created_lat is not None and created_lon is not None:
            attrs["created_location"] = Point(created_lon, created_lat)
        else:
            attrs["created_location"] = None

        if target_lat is not None and target_lon is not None:
            attrs["target_location"] = Point(target_lon, target_lat)
        else:
            attrs["target_location"] = None

        return attrs

    class Meta:
        model = AllyAlert
        fields = [
            "id",
            "creator",
            "title",
            "description",
            "created_location_longitude",
            "created_location_latitude",
            #
            "target_location_longitude",
            "target_location_latitude",
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
