from rest_framework import serializers
from django.contrib.gis.geos import Point

from .models import Address, MyInformation, User


def address_has_content(address_data):
    for value in address_data.values():
        if isinstance(value, str):
            if value.strip():
                return True
            continue

        if value not in (None, [], {}):
            return True

    return False


class AddressSerializer(serializers.ModelSerializer):
    # Explicit fields that accept input data and render output data
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = Address
        fields = ["longitude", "latitude", "as_string"]
        # as_string is handled automatically by your model's save() geocoder
        read_only_fields = ["as_string"]

    def to_representation(self, instance):
        """Controls what data is sent OUT to the API client."""
        representation = super().to_representation(instance)
        representation["latitude"] = instance.latitude
        representation["longitude"] = instance.longitude
        return representation

    def validate(self, attrs):
        """Validates coordinates and packages them into a Point object."""
        lat = attrs.pop("latitude", None)
        lon = attrs.pop("longitude", None)

        # Ensure both coordinates are present if one is provided
        if (lat is not None and lon is None) or (lon is not None and lat is None):
            raise serializers.ValidationError(
                "Both latitude and longitude must be provided together."
            )

        # Package coordinates into GeoDjango Point (X/Longitude first, Y/Latitude second)
        if lat is not None and lon is not None:
            attrs["location"] = Point(lon, lat)
        else:
            attrs["location"] = None

        return attrs


# class AddressSerializer(serializers.ModelSerializer):
#     # Read-only fields for API outputs
#     longitude = serializers.ReadOnlyField()
#     latitude = serializers.ReadOnlyField()

#     class Meta:
#         model = Address
#         fields = ["longitude", "latitude", "as_string"]
# read_only_fields = ["id"]


# FOR Address Serializer
# from rest_framework import serializers

# class LocationSerializer(serializers.ModelSerializer):
#     latitude = serializers.ReadOnlyField(source='point.y')
#     longitude = serializers.ReadOnlyField(source='point.x')

#     class Meta:
#         model = Location
#         fields = ['id', 'name', 'latitude', 'longitude']


# class AddressSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Address
#         fields = ["latitude", "longitude", "full_address"]
#         # read_only_fields = ["id"]


class MyInformationSerializer(serializers.ModelSerializer):
    address = AddressSerializer(required=False, allow_null=True)
    allergies = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )
    medications = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )
    trusted_contacts = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = MyInformation
        fields = [
            "id",
            "name",
            "birthday",
            "address",
            "gender",
            "weight",
            "height",
            "allergies",
            "medications",
            "medical_notes",
            "organ_donor",
            "is_pregnant",
            "due_date",
            "trusted_contacts",
        ]
        read_only_fields = ["id"]

    def validate_trusted_contacts(self, value):
        if value is None:
            return value

        for contact in value:
            if not isinstance(contact, dict):
                raise serializers.ValidationError(
                    "Each trusted contact must be an object."
                )

            unknown_keys = set(contact.keys()) - {"name", "phone"}
            if unknown_keys:
                names = ", ".join(sorted(unknown_keys))
                raise serializers.ValidationError(
                    f"Trusted contacts can only contain name and phone. Invalid keys: {names}"
                )

        return value

    def create(self, validated_data):
        address_data = validated_data.pop("address", None)

        address = None
        if address_data and address_has_content(address_data):
            address = Address.objects.create(**address_data)

        return MyInformation.objects.create(address=address, **validated_data)

    def update(self, instance, validated_data):
        address_data = validated_data.pop("address", serializers.empty)

        if address_data is not serializers.empty:
            if address_data is None:
                instance.address = None
            elif instance.address:
                for key, value in address_data.items():
                    setattr(instance.address, key, value)
                instance.address.save()
            elif address_has_content(address_data):
                instance.address = Address.objects.create(**address_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    my_information = MyInformationSerializer(required=False, allow_null=True)

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "username",
            "my_information",
            "latitude",
            "longitude",
            "is_streaming",
        ]
        read_only_fields = ["id"]

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None
