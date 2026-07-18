import uuid
from ally.models import User
from django.contrib.gis.db import models
from django.contrib.postgres import fields


class AllyAlert(models.Model):
    """
    The core alert model. A user creates an alert to warn others in a geographic area
    about something (e.g. danger, incident). The alert has a target location and a
    radius — any user within that radius is eligible to receive it.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        REMOVED = "REMOVED", "Removed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ally_alerts",
    )

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    # The user's GPS position at the moment they created the alert.
    created_location = models.PointField(
        geography=True,
        spatial_index=True,
        null=True,
        blank=True,
    )

    # The center point of the affected area. Users within radius_km of this point
    # will be notified. Spatially indexed for fast proximity queries.
    target_location = models.PointField(
        geography=True,
        spatial_index=True,
        null=True,
        blank=True,
    )

    # How far from target_location (in km) the alert should reach.
    radius_km = models.DecimalField(
        default=1.00,
        max_digits=6,
        decimal_places=2,
        help_text="How far from target_location (in km) the alert should reach.",
        null=True,
        blank=True,
    )

    # After this datetime the alert is considered stale and should be marked EXPIRED.
    # TODO: add time data from the front + current to set expiry date, not more than 5 days from now. If the user doesn't provide a time, default to 1 hour from now.
    expires_at = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,  # Indexed because we filter by status frequently.
    )

    # Denormalized reaction/report counts kept in sync via signals or service layer.
    # Avoids expensive COUNT queries on hot read paths.
    helpful_count = fields.ArrayField(models.UUIDField(), blank=True, default=list)
    # not_helpful_count = models.PositiveIntegerField(default=0)
    report_count = fields.ArrayField(models.UUIDField(), blank=True, default=list)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Composite index to speed up the common query: fetch all ACTIVE alerts
        # that haven't expired yet.
        indexes = [
            models.Index(fields=["status", "expires_at"]),
        ]


class AlertDelivery(models.Model):
    """
    Tracks which users have been delivered a given alert, and whether they've viewed it.
    One row per (alert, user) pair — enforced by the unique constraint below.
    This lets us avoid sending the same alert twice and measure reach/open rates.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    alert = models.ForeignKey(
        AllyAlert,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_alerts",
    )

    delivered_at = models.DateTimeField(auto_now_add=True)
    # Null until the user opens/acknowledges the alert.
    viewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["alert", "user"],
                name="unique_alert_delivery",
            )
        ]


class AlertReport(models.Model):
    """
    Allows users to flag an alert as helpful, inaccurate, spam, or otherwise problematic.
    One report per (alert, reporter) pair — a user cannot report the same alert twice.
    The report_count on AllyAlert should be incremented whenever a new report is saved.
    """

    class Reason(models.TextChoices):
        HELPFUL = "HELPFUL", "Helpful"
        NOT_HELPFUL = "NOT_HELPFUL", "Not Helpful"
        FALSE_INFORMATION = "FALSE_INFORMATION", "False Information"
        SPAM = "SPAM", "Spam"
        WRONG_LOCATION = "WRONG_LOCATION", "Wrong Location"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    alert = models.ForeignKey(
        AllyAlert,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="alert_reports",
    )

    reason = models.CharField(
        max_length=30,
        choices=Reason.choices,
    )

    # Optional free-text explanation from the reporter.
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            # Prevent a user from reporting the same alert more than once.
            models.UniqueConstraint(
                fields=["alert", "reporter"],
                name="unique_alert_report",
            )
        ]

        indexes = [
            models.Index(fields=["alert"]),  # Look up all reports for an alert.
            models.Index(fields=["reporter"]),  # Look up all reports by a user.
        ]

    def __str__(self):
        return f"{self.reporter} reported {self.alert_id}"


# class AllyAlertMedia(models.Model):
#     """
#     Optional media attachments (images, videos, audio) associated with an alert.
#     Multiple files can be attached to a single alert.
#     """

#     class MediaType(models.TextChoices):
#         IMAGE = "IMAGE", "Image"
#         VIDEO = "VIDEO", "Video"
#         AUDIO = "AUDIO", "Audio"

#     alert = models.ForeignKey(
#         AllyAlert,
#         on_delete=models.CASCADE,
#         related_name="media",
#     )

#     media_type = models.CharField(
#         max_length=10,
#         choices=MediaType.choices,
#     )

#     # Files are stored under MEDIA_ROOT/ally_alerts/.
#     file = models.FileField(upload_to="ally_alerts/")

#     uploaded_at = models.DateTimeField(auto_now_add=True)


# from django.db.models.signals import post_save
# from django.dispatch import receiver


# @receiver(post_save, sender=AllyAlert)
# def create_ally_alert_delivery(sender, instance, created, **kwargs):
#     """
#     Triggers automatically whenever an AllyAlert instance is saved.
#     """
#     if created:  # Ensures this only runs on creation, not on updates
#         AlertDelivery.objects.create(
#             alert=instance,
#             user=User.objects.get(pk="488cd143-4936-43b5-910a-76cc0b09908a"),
#             # Set your initial default status
#         )
