import json

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .models import Address, MyInformation, User

_KV_JS = """
<script>
(function () {
  if (window._kvAddRow) return;
  window._kvAddRow = function (containerId, fieldName) {
    var c = document.getElementById(containerId);
    var d = document.createElement('div');
    d.className = 'kv-row';
    d.style.cssText = 'display:flex;gap:8px;margin-bottom:6px;align-items:center';
    d.innerHTML =
      '<input type="text" name="' + fieldName + '_key[]" placeholder="key"'
      + ' style="width:40%;padding:4px 6px">'
      + '<span style="padding:0 4px">:</span>'
      + '<input type="text" name="' + fieldName + '_val[]" placeholder="value"'
      + ' style="flex:1;padding:4px 6px">'
      + '<button type="button" onclick="this.parentElement.remove()"'
      + ' style="color:#ba2121;cursor:pointer;border:none;background:none;font-size:18px;line-height:1">&#8722;</button>';
    c.insertBefore(d, c.lastElementChild);
  };
}());
</script>
"""


class KeyValueWidget(forms.Widget):
    def _row(self, name, key="", val=""):
        return (
            '<div class="kv-row" style="display:flex;gap:8px;margin-bottom:6px;align-items:center">'
            '<input type="text" name="{name}_key[]" value="{key}" placeholder="key"'
            ' style="width:40%;padding:4px 6px">'
            '<span style="padding:0 4px">:</span>'
            '<input type="text" name="{name}_val[]" value="{val}" placeholder="value"'
            ' style="flex:1;padding:4px 6px">'
            '<button type="button" onclick="this.parentElement.remove()"'
            ' style="color:#ba2121;cursor:pointer;border:none;background:none;font-size:18px;line-height:1">&#8722;</button>'
            "</div>"
        ).format(name=name, key=escape(str(key)), val=escape(str(val)))

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            try:
                value = json.loads(value) if value else {}
            except (json.JSONDecodeError, TypeError):
                value = {}
        if not isinstance(value, dict):
            value = {}

        cid = "kv_" + name.replace("-", "_").replace(".", "_")
        rows = "".join(self._row(name, k, v) for k, v in value.items()) or self._row(
            name
        )
        add_btn = (
            "<button type=\"button\" onclick=\"_kvAddRow('{cid}', '{name}')\""
            ' style="margin-top:4px;cursor:pointer;padding:2px 10px">&#43; Add</button>'
        ).format(cid=cid, name=name)

        return mark_safe(f'<div id="{cid}">{rows}{add_btn}</div>{_KV_JS}')

    def value_from_datadict(self, data, files, name):
        keys = data.getlist(f"{name}_key[]")
        vals = data.getlist(f"{name}_val[]")
        return {k.strip(): v.strip() for k, v in zip(keys, vals) if k.strip()}


class KeyValueField(forms.Field):
    widget = KeyValueWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def clean(self, value):
        return value if isinstance(value, dict) else {}

    def prepare_value(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value) if value else {}
            except (json.JSONDecodeError, TypeError):
                return {}
        return value if isinstance(value, dict) else {}


admin.site.site_header = "Ally Admin"
admin.site.site_title = "Ally Admin"
admin.site.index_title = "Operations Dashboard"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_address",
        "latitude",
        "longitude",
        "created_at",
        "updated_at",
    )
    search_fields = ("id", "full_address")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
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
        "address__full_address",
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
            obj.address.full_address
            or f"{obj.address.latitude}, {obj.address.longitude}"
        )

    @admin.display(description="Trusted Contacts")
    def trusted_contacts_count(self, obj):
        return len(obj.trusted_contacts or [])


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
        "date_joined",
        "updated_at",
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
    readonly_fields = ("id", "date_joined", "last_login", "updated_at")
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
                "fields": ("last_login", "date_joined", "updated_at"),
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
