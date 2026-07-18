import uuid
from django.contrib.gis.db import models
from ally.models import User


class LiveLocationSession(models.Model):
    """
    Model for when a user creates a live location session. This model stores information about the session, including the user who created it, the room name, and timestamps for when the session started and ended.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        # ideally this 2 should not be here but it is beacuse i am in dev mode
        null=True,
        blank=True,
    )
    room_name = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        # help_text="Availability e.g. '24/7'",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)


class SessionParticipant(models.Model):
    """

    Model for participants in a live location session. This model stores information about each participant, including the session they are part of, their IP address, the user who joined, and timestamps for when they joined and left the session.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    # Links to your existing session
    session = models.ForeignKey(
        LiveLocationSession,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    ip = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    # Links to the user who joined
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="joined_sessions",
        null=True,
        blank=True,
    )
    #
    metadata = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text='Additional metadata as JSON (e.g., {"key": "value"})',
    )
    # Tracking timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
