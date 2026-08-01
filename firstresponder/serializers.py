from rest_framework import serializers

from ally.models import Address
from ally.serializers import AddressSerializer, address_has_content
from firstresponder.models import FirstResponder, FirstResponderTag

from servicearea.models import ServiceArea




class FirstResponderSerializer(serializers.ModelSerializer):
    address = AddressSerializer(required=False, allow_null=True)
    phones = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )
    socials = serializers.DictField(required=False, allow_null=True)
    tags = serializers.ListField(
        child=serializers.ChoiceField(choices=FirstResponderTag.choices),
        required=False,
        allow_null=True,
    )
    metadata = serializers.DictField(required=False, allow_null=True)

    # service_areas = ServiceAreaSerializer(
    #     # queryset=ServiceArea.objects.all(),
    #     many=True,
    #     read_only=True,
    # )
    service_areas = serializers.PrimaryKeyRelatedField(
        queryset=ServiceArea.objects.all(),
        many=True,
    )

    class Meta:
        model = FirstResponder
        fields = [
            "id",
            "name",
            "firstresponder_type",
            "organization_type",
            "description",
            "phones",
            "availability",
            "socials",
            "response_time",
            "address",
            "tags",
            "metadata",
            "service_areas",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        address_data = validated_data.pop("address", None)

        address = None
        if address_data and address_has_content(address_data):
            address = Address.objects.create(**address_data)

        return FirstResponder.objects.create(address=address, **validated_data)

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
