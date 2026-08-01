from rest_framework import serializers

from servicearea.models import ServiceArea


class ServiceAreaSerializer(serializers.ModelSerializer):
    polygon = serializers.SerializerMethodField()

    class Meta:
        model = ServiceArea
        fields = [
            "id",
            "name",
            "polygon",
        ]

    def get_polygon(self, obj):
        if not obj.polygon:
            return None

        # Remove duplicate closing coordinate
        return [[lon, lat] for lon, lat in obj.polygon.coords[0][:-1]]
