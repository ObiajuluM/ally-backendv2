from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html

from .models import Address, FirstResponder, MyInformation, User


admin.site.site_header = "Ally Admin"
admin.site.site_title = "Ally Admin"
admin.site.index_title = "Operations Dashboard"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("id", "full_address", "latitude", "longitude")
    search_fields = ("id", "full_address")
    ordering = ("full_address", "id")
    list_per_page = 25
    empty_value_display = "-"


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
    )
    list_filter = ("gender", "organ_donor", "is_pregnant")
    search_fields = (
        "id",
        "name",
        "user__email",
        "user__username",
        "user__phone",
        "address__full_address",
    )
    list_select_related = ("address", "user")
    autocomplete_fields = ("address",)
    readonly_fields = ("id", "linked_user")
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
            obj.address.full_address
            or f"{obj.address.latitude}, {obj.address.longitude}"
        )

    @admin.display(description="Trusted Contacts")
    def trusted_contacts_count(self, obj):
        return len(obj.trusted_contacts or [])


@admin.register(FirstResponder)
class FirstResponderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "firstresponder_type",
        "organization_type",
        "availability",
        "response_time",
        "address_summary",
        "tag_count",
    )
    list_filter = ("firstresponder_type", "organization_type")
    search_fields = ("id", "name", "description", "address__full_address")
    list_select_related = ("address",)
    autocomplete_fields = ("address",)
    readonly_fields = ("id", "tag_count")
    fieldsets = (
        (
            "Overview",
            {
                "fields": (
                    "id",
                    "name",
                    "firstresponder_type",
                    "organization_type",
                    "description",
                ),
            },
        ),
        (
            "Operations",
            {
                "fields": ("availability", "response_time", "tags", "tag_count"),
            },
        ),
        (
            "Contacts",
            {
                "fields": ("phones", "socials", "metadata"),
            },
        ),
        (
            "Location",
            {
                "fields": ("address",),
            },
        ),
    )
    list_per_page = 25
    empty_value_display = "-"

    @admin.display(description="Address")
    def address_summary(self, obj):
        if not obj.address:
            return "-"
        return (
            obj.address.full_address
            or f"{obj.address.latitude}, {obj.address.longitude}"
        )

    @admin.display(description="Tags")
    def tag_count(self, obj):
        return len(obj.tags or [])


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = (
        "email",
        "username",
        "phone",
        "my_information_link",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_superuser", "is_active")
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
    readonly_fields = ("id", "date_joined", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
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
                "fields": ("last_login", "date_joined"),
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

    @admin.display(description="My Information")
    def my_information_link(self, obj):
        if not obj.my_information_id:
            return "-"

        url = reverse("admin:ally_myinformation_change", args=[obj.my_information_id])
        label = obj.my_information.name or str(obj.my_information_id)
        return format_html('<a href="{}">{}</a>', url, label)
