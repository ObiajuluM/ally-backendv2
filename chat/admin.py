from django.contrib import admin

from .models import Chat, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("id", "role", "content", "created_at")
    can_delete = False
    ordering = ("created_at",)


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "title",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "user__email",
        "title",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
    ordering = ("-updated_at",)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "chat",
        "role",
        "created_at",
    )
    list_filter = (
        "role",
        "created_at",
    )
    search_fields = (
        "chat__user__email",
        "content",
    )
    readonly_fields = (
        "id",
        "created_at",
    )
    ordering = ("-created_at",)