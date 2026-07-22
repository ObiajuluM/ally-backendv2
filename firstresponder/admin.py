import json

from django import forms
from django.contrib import admin
from django.utils.html import escape
from django.utils.safestring import mark_safe


from firstresponder.models import (
    FirstResponder,
    FirstResponderTag,
)

# -------------------------------------------------------------------
# Key / Value Widget (for socials & metadata)
# -------------------------------------------------------------------

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
      '<input type="text" name="' + fieldName + '_key[]" placeholder="key" style="width:40%;padding:4px 6px">'
      + '<span>:</span>'
      + '<input type="text" name="' + fieldName + '_val[]" placeholder="value" style="flex:1;padding:4px 6px">'
      + '<button type="button" onclick="this.parentElement.remove()" style="color:#ba2121;border:none;background:none;font-size:18px">&#8722;</button>';
    c.insertBefore(d, c.lastElementChild);
  };
}());
</script>
"""


class KeyValueWidget(forms.Widget):
    def _row(self, name, key="", val=""):
        return (
            '<div class="kv-row" style="display:flex;gap:8px;margin-bottom:6px">'
            '<input type="text" name="{name}_key[]" value="{key}" placeholder="key" style="width:40%">'
            "<span>:</span>"
            '<input type="text" name="{name}_val[]" value="{val}" placeholder="value" style="flex:1">'
            '<button type="button" onclick="this.parentElement.remove()" style="color:#ba2121;border:none;background:none;font-size:18px">&#8722;</button>'
            "</div>"
        ).format(
            name=name,
            key=escape(str(key)),
            val=escape(str(val)),
        )

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = {}

        value = value or {}

        cid = f"kv_{name}"

        rows = "".join(self._row(name, k, v) for k, v in value.items()) or self._row(
            name
        )

        return mark_safe(f"""
            <div id="{cid}">
                {rows}
                <button type="button"
                        onclick="_kvAddRow('{cid}','{name}')">
                        + Add
                </button>
            </div>
            {_KV_JS}
            """)

    def value_from_datadict(self, data, files, name):
        keys = data.getlist(f"{name}_key[]")
        vals = data.getlist(f"{name}_val[]")

        return {k.strip(): v.strip() for k, v in zip(keys, vals) if k.strip()}


class KeyValueField(forms.Field):
    widget = KeyValueWidget

    def clean(self, value):
        return value or {}


# -------------------------------------------------------------------
# First Responder Form
# -------------------------------------------------------------------


class FirstResponderAdminForm(forms.ModelForm):
    tags = forms.MultipleChoiceField(
        choices=FirstResponderTag.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    socials = KeyValueField(required=False)

    metadata = KeyValueField(required=False)

    class Meta:
        model = FirstResponder
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["tags"].initial = self.instance.tags or []


# -------------------------------------------------------------------
# Duplicate Action
# -------------------------------------------------------------------


@admin.action(description="Duplicate selected responders")
def duplicate_first_responders(modeladmin, request, queryset):
    for responder in queryset:

        service_areas = list(responder.service_areas.all())

        responder.pk = None
        responder.address = None

        responder.name = f"{responder.name} (copy)" if responder.name else "Copy"

        responder.save()

        responder.service_areas.set(service_areas)

    modeladmin.message_user(
        request,
        f"{queryset.count()} responder(s) duplicated.",
    )


# -------------------------------------------------------------------
# First Responder Admin
# -------------------------------------------------------------------


@admin.register(FirstResponder)
class FirstResponderAdmin(admin.ModelAdmin):
    form = FirstResponderAdminForm

    actions = [duplicate_first_responders]

    autocomplete_fields = (
        "address",
        "service_areas",
    )

    list_display = (
        "name",
        "firstresponder_type",
        "organization_type",
        "availability",
        "response_time",
        "address_summary",
        "tag_count",
        "service_area_count",
        "created_at",
    )

    list_filter = (
        "firstresponder_type",
        "organization_type",
    )

    search_fields = (
        "name",
        "description",
        "address__as_string",
    )

    list_select_related = ("address",)

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "tag_count",
        "service_area_count",
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
                )
            },
        ),
        (
            "Operations",
            {
                "fields": (
                    "availability",
                    "response_time",
                    "tags",
                )
            },
        ),
        (
            "Contact",
            {
                "fields": (
                    "phones",
                    "socials",
                    "metadata",
                )
            },
        ),
        (
            "Coverage",
            {
                "fields": (
                    "address",
                    "service_areas",
                )
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "tag_count",
                    "service_area_count",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(description="Address")
    def address_summary(self, obj):
        if not obj.address:
            return "-"

        return (
            obj.address.as_string or f"{obj.address.latitude}, {obj.address.longitude}"
        )

    @admin.display(description="Tags")
    def tag_count(self, obj):
        return len(obj.tags or [])

    @admin.display(description="Service Areas")
    def service_area_count(self, obj):
        return obj.service_areas.count()
