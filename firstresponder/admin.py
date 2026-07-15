import json

from django import forms
from django.contrib import admin

from django.db import connection
from django.db.models import Func, IntegerField, Value
from django.db.models.functions import Coalesce
from django.utils.html import escape
from django.utils.safestring import mark_safe

from firstresponder.models import FirstResponder, FirstResponderTag

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
    container.querySelectorAll('.sa-zone-input').forEach(function (ta) {
      var val = ta.value.trim();
      if (!val) return;
      try {
        var zone = JSON.parse(val);
        if (Array.isArray(zone)) data.push(zone);
      } catch (e) { /* skip invalid */ }
    });
    return JSON.stringify(data);
  }

  function renumberZones(container) {
    container.querySelectorAll('.sa-zone').forEach(function (zone, i) {
      var lbl = zone.querySelector('.sa-zone-label');
      if (lbl) lbl.textContent = 'Zone ' + (i + 1) + ':';
    });
  }

  window._saRemoveZone = function (btn) {
    var zone = btn.closest('.sa-zone');
    var container = zone.closest('.sa-container');
    zone.remove();
    renumberZones(container);
  };

  window._saAddZone = function (containerId) {
    var container = document.getElementById(containerId);
    var zonesDiv = container.querySelector('.sa-zones');
    var idx = container.querySelectorAll('.sa-zone').length + 1;
    var div = document.createElement('div');
    div.className = 'sa-zone';
    div.style.cssText = 'display:flex;align-items:flex-start;gap:8px;margin-bottom:8px';
    div.innerHTML =
      '<label class="sa-zone-label" style="min-width:60px;padding-top:6px;font-weight:bold">Zone ' + idx + ':</label>' +
      '<textarea class="sa-zone-input" rows="3" style="flex:1;font-family:monospace;padding:4px 6px" placeholder="[[lat, lng], [lat, lng], ...]"></textarea>' +
      '<button type="button" onclick="_saRemoveZone(this)" style="color:#ba2121;cursor:pointer;border:none;background:none;font-size:18px;padding-top:4px">&#8722;</button>';
    zonesDiv.appendChild(div);
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
    def _zone_row(self, idx, zone_value):
        val = json.dumps(zone_value) if zone_value else ""
        return (
            '<div class="sa-zone" style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px">'
            f'<label class="sa-zone-label" style="min-width:60px;padding-top:6px;font-weight:bold">Zone {idx}:</label>'
            f'<textarea class="sa-zone-input" rows="3" style="flex:1;font-family:monospace;padding:4px 6px" placeholder="[[lat, lng], [lat, lng], ...]">{escape(val)}</textarea>'
            '<button type="button" onclick="_saRemoveZone(this)" style="color:#ba2121;cursor:pointer;border:none;background:none;font-size:18px;padding-top:4px">&#8722;</button>'
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
        zones_html = "".join(self._zone_row(i + 1, z) for i, z in enumerate(value))
        if not zones_html:
            zones_html = self._zone_row(1, None)
        add_btn = f'<button type="button" onclick="_saAddZone(\'{cid}\')" style="cursor:pointer;padding:2px 10px;margin-top:4px">&#43; Add Zone</button>'
        hidden = f'<input type="hidden" name="{name}_json" class="sa-hidden">'

        return mark_safe(
            f'<div id="{cid}" class="sa-container"><div class="sa-zones">{zones_html}</div>{add_btn}{hidden}</div>{_SA_JS}'
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


class ServiceZoneCountFilter(admin.SimpleListFilter):
    title = "service zones"
    parameter_name = "service_zones"

    def lookups(self, request, model_admin):
        return [
            ("0", "None"),
            ("1", "1"),
            ("2", "2"),
            ("3plus", "3+"),
        ]

    def queryset(self, request, queryset):
        fn = (
            "jsonb_array_length"
            if connection.vendor == "postgresql"
            else "JSON_ARRAY_LENGTH"
        )
        annotated = queryset.annotate(
            _szc=Coalesce(
                Func("service_areas", function=fn, output_field=IntegerField()),
                Value(0),
            )
        )
        val = self.value()
        if val == "0":
            return annotated.filter(_szc=0)
        if val == "1":
            return annotated.filter(_szc=1)
        if val == "2":
            return annotated.filter(_szc=2)
        if val == "3plus":
            return annotated.filter(_szc__gte=3)
        return queryset


@admin.action(description="Duplicate selected first responders")
def duplicate_first_responders(modeladmin, request, queryset):
    # Capture the count before the loop because pk=None mutates the objects
    count = queryset.count()
    for obj in queryset:
        # Setting pk to None tells Django to treat this as a new (unsaved) object.
        # On .save() it will INSERT a new row and auto-generate a fresh UUID.
        obj.pk = None

        # Distinguish the copy from the original in the list view
        obj.name = f"{obj.name} (copy)" if obj.name else "Copy"

        # address is a OneToOneField — two records cannot share the same address row,
        # so we clear it; the user can assign a new one after duplicating.
        obj.address = None

        # JSONField lists are mutable; slice-copy so the duplicate gets its own
        # list object instead of a reference to the original's list.
        obj.service_areas = obj.service_areas[:] if obj.service_areas else []

        # Persist the new record to the database
        obj.save()

    # Show a confirmation banner at the top of the change list
    modeladmin.message_user(request, f"{count} first responder(s) duplicated.")


@admin.register(FirstResponder)
class FirstResponderAdmin(admin.ModelAdmin):
    form = FirstResponderAdminForm
    actions = [duplicate_first_responders]
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
    list_filter = ("firstresponder_type", "organization_type", ServiceZoneCountFilter)
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        fn = (
            "jsonb_array_length"
            if connection.vendor == "postgresql"
            else "JSON_ARRAY_LENGTH"
        )
        return qs.annotate(
            _service_area_count=Func(
                "service_areas",
                function=fn,
                output_field=IntegerField(),
            )
        )

    @admin.display(description="Service Zones", ordering="_service_area_count")
    def service_area_count(self, obj):
        areas = obj.service_areas or []
        return len(areas) if areas else "-"
