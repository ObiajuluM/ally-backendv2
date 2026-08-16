import json

from django import forms
from django.contrib import admin
from django.contrib.gis.geos import Point

from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .models import Address, MyInformation, User, UserDevice

admin.site.site_header = "Ally Admin"
admin.site.site_title = "Ally Admin"
admin.site.index_title = "Operations Dashboard"


class AddressAdminForm(forms.ModelForm):
    # Create two explicit form fields for inputs
    longitude = forms.FloatField(required=False, label="Longitude")
    latitude = forms.FloatField(required=False, label="Latitude")

    class Meta:
        model = Address
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate the form inputs if an instance exists with a location
        if self.instance and self.instance.location:
            self.initial["longitude"] = self.instance.location.x
            self.initial["latitude"] = self.instance.location.y

    def save(self, commit=True):
        instance = super().save(commit=False)
        lon = self.cleaned_data.get("longitude")
        lat = self.cleaned_data.get("latitude")

        # Convert the individual inputs back into a GeoDjango Point object
        if lon is not None and lat is not None:
            instance.location = Point(lon, lat)
        else:
            instance.location = None

        if commit:
            instance.save()
        return instance


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    form = AddressAdminForm  # Hook up the custom form

    list_display = (
        "id",
        "as_string",
        "longitude",  # Pulls from model property for list view
        "latitude",  # Pulls from model property for list view
        "created_at",
        "updated_at",
    )

    # Define fields layout to show them in the edit panel
    fields = (
        "as_string",
        "longitude",
        "latitude",
        "created_at",
        "updated_at",
    )

    search_fields = ("id", "as_string")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 25
    empty_value_display = "-"


# @admin.register(Address)
# class AddressAdmin(admin.ModelAdmin):
#     list_display = (
#         "id",
#         "as_string",
#         "longitude",
#         "latitude",
#         "created_at",
#         "updated_at",
#     )
#     search_fields = ("id", "as_string")
#     ordering = ("-created_at",)
#     readonly_fields = ("created_at", "updated_at")
#     list_per_page = 25
#     empty_value_display = "-"


@admin.register(MyInformation)
class MyInformationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "gender",
        "birthday",
        "organ_donor",
        "is_pregnant",
        "linked_user",
        "address_summary",
        "trusted_contacts_count",
        "created_at",
        "updated_at",
    )
    list_filter = ("gender", "organ_donor", "is_pregnant")
    search_fields = (
        "id",
        "name",
        "user__email",
        "user__username",
        "user__phone",
        "address__as_string",
    )
    list_select_related = ("address", "user")
    autocomplete_fields = ("address",)
    readonly_fields = ("id", "linked_user", "created_at", "updated_at")
    fieldsets = (
        (
            "Basic Info",
            {
                "fields": ("id", "name", "birthday", "gender", "linked_user"),
            },
        ),
        (
            "Health Details",
            {
                "fields": (
                    "weight",
                    "height",
                    "allergies",
                    "medications",
                    "medical_notes",
                    "organ_donor",
                    "is_pregnant",
                    "due_date",
                ),
            },
        ),
        (
            "Contacts And Address",
            {
                "fields": ("address", "trusted_contacts"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    list_per_page = 25
    empty_value_display = "-"

    @admin.display(description="User")
    def linked_user(self, obj):
        try:
            user = obj.user
        except User.DoesNotExist:
            return "-"

        url = reverse("admin:ally_user_change", args=[user.pk])
        label = user.email or user.username or str(user.pk)
        return format_html('<a href="{}">{}</a>', url, label)

    @admin.display(description="Address")
    def address_summary(self, obj):
        if not obj.address:
            return "-"
        return (
            obj.address.as_string or f"{obj.address.longitude}, {obj.address.latitude}"
        )

    @admin.display(description="Trusted Contacts")
    def trusted_contacts_count(self, obj):
        return len(obj.trusted_contacts or [])


class UserAdminForm(forms.ModelForm):
    # This field handles the special read-only text and link formatting - fixes the requesting password on model save bs
    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            "Raw passwords are not stored, so there is no way to see "
            "the user's password."
        ),
    )
    latitude = forms.FloatField(
        required=False,
        label="Latitude",
        help_text="The user's last seen latitude - Example: 6.5244",
    )

    longitude = forms.FloatField(
        required=False,
        label="Longitude",
        help_text="The user's last seen longitude - Example: 3.3792",
    )

    class Meta:
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fallback handling to pull help text if the password field is blank/unset - fixes the requesting password on model save bs
        password = self.fields.get("password")
        if password and self.instance.pk:
            # Reuses standard Django text formatting for active vs unset passwords
            password.help_text = password.help_text

        if self.instance and self.instance.location:
            self.fields["latitude"].initial = self.instance.location.y
            self.fields["longitude"].initial = self.instance.location.x

    def clean(self):
        cleaned_data = super().clean()

        lat = cleaned_data.get("latitude")
        lon = cleaned_data.get("longitude")

        if lat is not None and not -90 <= lat <= 90:
            self.add_error(
                "latitude",
                "Latitude must be between -90 and 90.",
            )

        if lon is not None and not -180 <= lon <= 180:
            self.add_error(
                "longitude",
                "Longitude must be between -180 and 180.",
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        latitude = self.cleaned_data.get("latitude")
        longitude = self.cleaned_data.get("longitude")

        if latitude is not None and longitude is not None:
            user.location = Point(
                longitude,
                latitude,
                # srid=4326,
            )

        elif latitude is None and longitude is None:
            user.location = None

        if commit:
            user.save()

        return user


# ============================================================
# User Admin
# ============================================================


@admin.register(User)
class UserAdmin(BaseUserAdmin):

    model = User
    form = UserAdminForm

    list_display = (
        "email",
        "username",
        "phone",
        "latitude_display",
        "longitude_display",
        "map_link",
        "my_information_link",
        "is_staff",
        "is_active",
        "date_joined",
        "updated_at",
    )

    list_filter = ("is_staff", "is_superuser", "is_active", "is_streaming")

    search_fields = (
        "email",
        "username",
        "phone",
        "first_name",
        "last_name",
        "my_information__name",
    )

    ordering = ("email",)

    list_select_related = ("my_information",)

    autocomplete_fields = ("my_information",)

    readonly_fields = (
        "id",
        "date_joined",
        "last_login",
        "updated_at",
        "google_map",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            "Profile",
            {
                "fields": (
                    "id",
                    "username",
                    "first_name",
                    "last_name",
                    "phone",
                    "my_information",
                ),
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "is_streaming",
                    "latitude",
                    "longitude",
                    "google_map",
                ),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "updated_at",
                ),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "phone",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    list_per_page = 25

    empty_value_display = "-"

    # ========================================================
    # Location Display Helpers
    # ========================================================

    @admin.display(description="Latitude")
    def latitude_display(self, obj):

        if obj.location:
            return round(obj.location.y, 6)

        return "-"

    @admin.display(description="Longitude")
    def longitude_display(self, obj):

        if obj.location:
            return round(obj.location.x, 6)

        return "-"

    @admin.display(description="Google Maps")
    def google_map(self, obj):

        if not obj.location:
            return "-"

        lat = obj.location.y
        lon = obj.location.x

        url = f"https://www.google.com/maps?q={lat},{lon}"

        return format_html(
            '<a href="{}" target="_blank">' "Open Location" "</a>",
            url,
        )

    @admin.display(description="Map")
    def map_link(self, obj):

        if not obj.location:
            return "-"

        lat = obj.location.y
        lon = obj.location.x

        return format_html(
            '<a href="https://www.google.com/maps?q={},{}" target="_blank">'
            "View"
            "</a>",
            lat,
            lon,
        )

    @admin.display(description="My Information")
    def my_information_link(self, obj):

        if not obj.my_information_id:
            return "-"

        url = reverse(
            "admin:ally_myinformation_change",
            args=[obj.my_information_id],
        )

        label = obj.my_information.name or str(obj.my_information_id)

        return format_html(
            '<a href="{}">{}</a>',
            url,
            label,
        )


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ("user_link", "platform", "is_active", "created_at", "updated_at")
    list_filter = ("platform", "is_active")
    search_fields = ("user__email", "user__username", "fcm_token")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("user",)
    list_per_page = 25
    empty_value_display = "-"

    @admin.display(description="User")
    def user_link(self, obj):
        url = reverse("admin:ally_user_change", args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email or obj.user_id)
