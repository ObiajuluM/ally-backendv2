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
    list_display = ("id", "user", "room_name", "started_at", "ended_at")
    list_filter = ("started_at",)
    search_fields = ("room_name", "user__email")
    inlines = [SessionParticipantInline]


@admin.register(SessionParticipant)
class SessionParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "session_link", "user", "ip", "joined_at", "left_at")
    list_filter = ("joined_at",)
    search_fields = ("user__email", "ip")

    @admin.display(description="Session")
    def session_link(self, obj):
        url = reverse(
            "admin:livelocation_livelocationsession_change", args=[obj.session_id]
        )
        return format_html('<a href="{}">{}</a>', url, obj.session_id)
