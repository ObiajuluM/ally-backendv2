from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import LiveLocationSession, SessionParticipant


class SessionParticipantInline(admin.TabularInline):
    model = SessionParticipant
    extra = 0
    readonly_fields = ("user", "ip", "joined_at", "left_at")
    fields = ("user", "ip", "joined_at", "left_at")
    exclude = ("metadata",)
    can_delete = False
    show_change_link = True


@admin.register(LiveLocationSession)
class LiveLocationSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user_link", "room_name", "started_at", "ended_at")
    list_filter = ("started_at",)
    search_fields = ("room_name", "user__email", "user__username")
    ordering = ("-started_at",)
    readonly_fields = ("id", "started_at")
    list_select_related = ("user",)
    list_per_page = 25
    empty_value_display = "-"
    inlines = [SessionParticipantInline]
    fieldsets = (
        (None, {"fields": ("id", "user", "room_name")}),
        ("Metadata", {"fields": ("metadata",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("started_at", "ended_at")}),
    )

    @admin.display(description="User")
    def user_link(self, obj):
        if not obj.user_id:
            return "-"
        url = reverse("admin:ally_user_change", args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email or obj.user_id)


@admin.register(SessionParticipant)
class SessionParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "session_link", "user", "ip", "joined_at", "left_at")
    list_filter = ("joined_at",)
    search_fields = ("user__email", "ip", "session__room_name")
    ordering = ("-joined_at",)
    readonly_fields = ("id", "joined_at", "metadata_pretty")
    list_select_related = ("user", "session")
    list_per_page = 25
    empty_value_display = "-"
    fieldsets = (
        (None, {"fields": ("id", "session", "user", "ip")}),
        ("Metadata", {"fields": ("metadata_pretty",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("joined_at", "left_at")}),
    )

    @admin.display(description="Session")
    def session_link(self, obj):
        url = reverse(
            "admin:livelocation_livelocationsession_change", args=[obj.session_id]
        )
        return format_html('<a href="{}">{}</a>', url, obj.session_id)

    @admin.display(description="Metadata")
    def metadata_pretty(self, obj):
        import json

        if not obj.metadata:
            return "-"
        return format_html("<pre>{}</pre>", json.dumps(obj.metadata, indent=2))
