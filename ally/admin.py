import json

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .models import Address, FirstResponder, FirstResponderTag, MyInformation, User

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


_SA_JS = """
<script>
(function () {
  if (window._saReady) return;
  window._saReady = true;

  function saSerialize(containerId) {
    var container = document.getElementById(containerId);
    var data = [];
    container.querySelectorAll('.sa-zone').forEach(function (zone) {
      var points = [];
      var lats = zone.querySelectorAll('.sa-lat');
      var lngs = zone.querySelectorAll('.sa-lng');
      for (var i = 0; i < lats.length; i++) {
        var lat = parseFloat(lats[i].value);
        var lng = parseFloat(lngs[i].value);
        if (!isNaN(lat) && !isNaN(lng)) points.push([lat, lng]);
      }
      if (points.length) data.push(points);
    });
    return JSON.stringify(data);
  }

  function makePoint(lat, lng) {
    var d = document.createElement('div');
    d.className = 'sa-point';
    d.style.cssText = 'display:flex;gap:6px;margin-bottom:4px;align-items:center';
    d.innerHTML =
      '<input type="text" class="sa-lat" value="' + (lat !== undefined ? lat : '') + '" placeholder="lat" style="width:45%;padding:4px 6px">' +
      '<input type="text" class="sa-lng" value="' + (lng !== undefined ? lng : '') + '" placeholder="lng" style="flex:1;padding:4px 6px">' +
      '<button type="button" onclick="_saRemovePoint(this)" style="color:#ba2121;cursor:pointer;border:none;background:none;font-size:18px;line-height:1">&#8722;</button>';
    return d;
  }

  function makeZone(idx) {
    var zone = document.createElement('div');
    zone.className = 'sa-zone';
    zone.style.cssText = 'border:1px solid #444;padding:10px;margin-bottom:10px;border-radius:4px;background:#2a2a2a;color:#eee';
    zone.innerHTML =
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">' +
        '<strong>Zone ' + idx + '</strong>' +
        '<button type="button" onclick="_saRemoveZone(this)" style="color:#ba2121;cursor:pointer;border:none;background:none;font-size:13px">&#8722; Remove Zone</button>' +
      '</div>' +
      '<div class="sa-points"></div>' +
      '<button type="button" onclick="_saAddPoint(this)" style="margin-top:4px;cursor:pointer;padding:2px 8px">&#43; Add Point</button>';
    zone.querySelector('.sa-points').appendChild(makePoint());
    return zone;
  }

  window._saRemoveZone = function (btn) { btn.closest('.sa-zone').remove(); };
  window._saRemovePoint = function (btn) { btn.closest('.sa-point').remove(); };

  window._saAddPoint = function (btn) {
    btn.closest('.sa-zone').querySelector('.sa-points').appendChild(makePoint());
  };

  window._saAddZone = function (containerId) {
    var container = document.getElementById(containerId);
    var idx = container.querySelectorAll('.sa-zone').length + 1;
    container.insertBefore(makeZone(idx), container.lastElementChild);
  };

  function attachHandler(container) {
    var form = container.closest('form');
    if (form && !form._saAttached) {
      form._saAttached = true;
      form.addEventListener('submit', function () {
        document.querySelectorAll('.sa-container').forEach(function (c) {
          var h = c.querySelector('.sa-hidden');
          if (h) h.value = saSerialize(c.id);
        });
      });
    }
  }

  function init() {
    document.querySelectorAll('.sa-container').forEach(attachHandler);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
</script>
"""


class ServiceAreasWidget(forms.Widget):
    def _zone_html(self, zone_idx, points):
        pts = ""
        for lat, lng in points or []:
            pts += (
                '<div class="sa-point" style="display:flex;gap:6px;margin-bottom:4px;align-items:center">'
                f'<input type="text" class="sa-lat" value="{escape(str(lat))}" placeholder="lat" style="width:45%;padding:4px 6px">'
                f'<input type="text" class="sa-lng" value="{escape(str(lng))}" placeholder="lng" style="flex:1;padding:4px 6px">'
                '<button type="button" onclick="_saRemovePoint(this)" style="color:#ba2121;cursor:pointer;border:none;background:none;font-size:18px;line-height:1">&#8722;</button>'
                "</div>"
            )
        if not pts:
            pts = (
                '<div class="sa-point" style="display:flex;gap:6px;margin-bottom:4px;align-items:center">'
                '<input type="text" class="sa-lat" placeholder="lat" style="width:45%;padding:4px 6px">'
                '<input type="text" class="sa-lng" placeholder="lng" style="flex:1;padding:4px 6px">'
                '<button type="button" onclick="_saRemovePoint(this)" style="color:#ba2121;cursor:pointer;border:none;background:none;font-size:18px;line-height:1">&#8722;</button>'
                "</div>"
            )
        return (
            '<div class="sa-zone" style="border:1px solid #444;padding:10px;margin-bottom:10px;border-radius:4px;background:#2a2a2a;color:#eee">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
            f"<strong>Zone {zone_idx}</strong>"
            '<button type="button" onclick="_saRemoveZone(this)" style="color:#ba2121;cursor:pointer;border:none;background:none;font-size:13px">&#8722; Remove Zone</button>'
            "</div>"
            f'<div class="sa-points">{pts}</div>'
            '<button type="button" onclick="_saAddPoint(this)" style="margin-top:4px;cursor:pointer;padding:2px 8px">&#43; Add Point</button>'
            "</div>"
        )

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            try:
                value = json.loads(value) if value else []
            except (json.JSONDecodeError, TypeError):
                value = []
        if not isinstance(value, list):
            value = []

        cid = "sa_" + name.replace("-", "_").replace(".", "_")
        zones = "".join(self._zone_html(i + 1, z) for i, z in enumerate(value))
        add_btn = f'<button type="button" onclick="_saAddZone(\'{cid}\')" style="cursor:pointer;padding:2px 10px">&#43; Add Zone</button>'
        hidden = f'<input type="hidden" name="{name}_json" class="sa-hidden">'

        return mark_safe(
            f'<div id="{cid}" class="sa-container">{zones}{add_btn}{hidden}</div>{_SA_JS}'
        )

    def value_from_datadict(self, data, files, name):
        raw = data.get(f"{name}_json", "")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []


class ServiceAreasField(forms.Field):
    widget = ServiceAreasWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def clean(self, value):
        return value if isinstance(value, list) else []

    def prepare_value(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value) if value else []
            except (json.JSONDecodeError, TypeError):
                return []
        return value if isinstance(value, list) else []


class FirstResponderAdminForm(forms.ModelForm):
    tags = forms.MultipleChoiceField(
        choices=FirstResponderTag.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    socials = KeyValueField(
        help_text="Social media links (e.g., facebook, twitter, website).",
    )
    metadata = KeyValueField(
        help_text="Additional metadata as key-value pairs.",
    )
    service_areas = ServiceAreasField(
        help_text="Each zone is a polygon defined by lat/lng coordinate pairs.",
    )

    class Meta:
        model = FirstResponder
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            if self.instance.tags:
                self.fields["tags"].initial = self.instance.tags


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


@admin.register(FirstResponder)
class FirstResponderAdmin(admin.ModelAdmin):
    form = FirstResponderAdminForm
    list_display = (
        "id",
        "name",
        "firstresponder_type",
        "organization_type",
        "availability",
        "response_time",
        "address_summary",
        "tag_count",
        "service_area_count",
        "created_at",
        "updated_at",
    )
    list_filter = ("firstresponder_type", "organization_type")
    search_fields = ("id", "name", "description", "address__full_address")
    list_select_related = ("address",)
    autocomplete_fields = ("address",)
    readonly_fields = (
        "id",
        "tag_count",
        "service_area_count",
        "created_at",
        "updated_at",
    )
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
                "fields": ("address", "service_areas", "service_area_count"),
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

    @admin.display(description="Service Zones")
    def service_area_count(self, obj):
        areas = obj.service_areas or []
        return len(areas) if areas else "-"


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
