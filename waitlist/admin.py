from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages

from .models import WaitlistEntry


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")
    list_display = ("email",)
    search_fields = ("email",)

    change_list_template = "admin/waitlist_changelist.html"

    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            path(
                "bulk-add/",
                self.admin_site.admin_view(self.bulk_add),
                name="waitlist_bulk_add",
            ),
        ]

        return custom_urls + urls

    def bulk_add(self, request):
        if request.method == "POST":
            emails = request.POST.get("emails")

            if emails:
                email_list = [
                    email.strip() for email in emails.split("\n") if email.strip()
                ]

                created = 0

                for email in email_list:
                    obj, is_created = WaitlistEntry.objects.get_or_create(email=email)

                    if is_created:
                        created += 1

                messages.success(request, f"{created} waitlist entries added.")

                return redirect("../")

        return render(request, "admin/bulk_add_waitlist.html")
