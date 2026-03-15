from rest_framework import serializers

from .models import Address, FirstResponder, FirstResponderTag, MyInformation, User


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
    class Meta:
        model = Address
        fields = ["latitude", "longitude", "full_address"]
        # read_only_fields = ["id"]


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
    my_information = serializers.HyperlinkedRelatedField(
        view_name="myinformation-detail",
        queryset=MyInformation.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone",
            "username",
            "my_information",
        ]
        read_only_fields = ["id"]
