from __future__ import (
    annotations,
)  # for typechecking the channel scope # Must be the very first line of the file

from typing import TYPE_CHECKING
from django.utils import timezone

from ally.models import User
from livelocation.models import (
    LiveLocationSession,
    SessionParticipant,
)  # for typechecking the channel scope

if TYPE_CHECKING:  # for typechecking the channel scope
    # This import only happens during type checking, never at runtime
    from channels.consumer import _ChannelScope  # for typechecking the channel scope

import json

from asgiref.sync import async_to_sync


from channels.generic.websocket import WebsocketConsumer
from config import settings


class LiveLocationConsumer(WebsocketConsumer):
    # Viewers and the publisher all join the same room, but only the room owner
    # is allowed to send location updates into it.
    # Each accepted location payload is normalized to this fixed field list.
    LOCATION_FIELDS = (
        "lat",
        "long",
        "accuracy",
        "alt",
        "alt_accuracy",
        "time",
    )

    def connect(self):
        # The room name comes from the websocket URL and identifies whose live
        # location stream this socket is subscribing to.
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]

        # Cache the publish permission once on connect so receive() can make a quick decision for every incoming socket message.
        self.can_publish = self.user_can_publish()

        # TODO: look to sending sms here if the user can publish

        # Every socket in the same room joins the same channel-layer group, which
        # lets one published update fan out to every connected viewer.
        self.room_group_name = f"live_{self.room_name}"
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )

        # helper method for when a user connects
        self.on_connect()

        # The connection itself stays public so anonymous users can still watch.
        self.accept()

    def disconnect(self, close_code):
        # Remove this socket from the room group so it stops receiving broadcasts.
        self.on_disconnect()
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    def receive(self, text_data):
        """Receiving from the socket means the client is trying to publish."""
        # Viewers are allowed to stay connected, but they cannot inject updates.
        if not self.can_publish:
            self.send(
                text_data=json.dumps(
                    {"error": "Only the authenticated room owner can publish updates."}
                )
            )
            return

        # Reject malformed JSON early so only valid payloads reach the group.
        try:
            text_data_json = json.loads(text_data)
        except json.JSONDecodeError:
            self.send(text_data=json.dumps({"error": "Invalid JSON payload."}))
            return

        # Require the full location shape so subscribers always receive a complete,
        # predictable payload.
        missing_fields = [
            field for field in self.LOCATION_FIELDS if field not in text_data_json
        ]
        if missing_fields:
            self.send(
                text_data=json.dumps(
                    {
                        "error": "Missing required location fields.",
                        "missing_fields": missing_fields,
                    }
                )
            )
            return

        # Forward only the approved fields, ignoring any extra client-supplied data.
        location_data = {field: text_data_json[field] for field in self.LOCATION_FIELDS}

        # Publish one group event so Channels can deliver the same update to every
        # socket that joined this room.
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {"type": "location.update", "location_data": location_data},
        )

    def location_update(self, event):
        # Channels maps the event type `location.update` to this method name.
        location_data = event["location_data"]

        # Each client receives the same structured JSON payload that was broadcast
        # through the channel layer.
        self.send(text_data=json.dumps(location_data))

    def user_can_publish(self) -> bool:
        """A client may publish only when it is authenticated and connected to the room named after that user's UUID and is not blocked."""
        user = self.scope.get("user")
        # return bool(user and user.is_authenticated and str(user.id) == self.room_name)
        # REMEMBER: In development mode, we allow any user to publish for testing purposes. In production, only the authenticated user whose ID matches the room name can publish.
        return (
            True
            if settings.DEBUG
            else bool(user and user.is_authenticated and str(user.id) == self.room_name)
            and user.is_active
        )

    def get_real_ip(self, scope: _ChannelScope):
        """
        Retrieve the real IP address of the client, considering possible proxy headers.
        """
        client_ip = scope.get("client")[0]  # Default to the direct client IP
        headers = dict(scope.get("headers", []))

        if b"x-forwarded-for" in headers:
            # Headers are byte strings, decode them first
            forwarded_for = headers[b"x-forwarded-for"].decode("utf-8")
            # If there are multiple IPs in the header, take the first one (the original client)
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # Fallback to the direct client IP
            client_ip = scope["client"][0]

        return client_ip

    def serialize_scope(self, scope: dict) -> dict:
        """
        Convert a Django Channels ASGI scope into a JSON-serializable dict
        suitable for models.JSONField.
        """

        headers = {
            key.decode("utf-8", errors="replace"): value.decode(
                "utf-8", errors="replace"
            )
            for key, value in scope.get("headers", [])
        }

        client = scope.get("client")
        server = scope.get("server")

        return {
            "type": scope.get("type"),
            "path": scope.get("path"),
            "raw_path": (
                scope.get("raw_path", b"").decode("utf-8", errors="replace")
                if scope.get("raw_path")
                else None
            ),
            "scheme": scope.get("scheme"),
            "query_string": scope.get("query_string", b"").decode(
                "utf-8", errors="replace"
            ),
            "client": (
                {
                    "ip": client[0],
                    "port": client[1],
                }
                if client
                else None
            ),
            "server": (
                {
                    "host": server[0],
                    "port": server[1],
                }
                if server
                else None
            ),
            "headers": headers,
            "subprotocols": scope.get("subprotocols", []),
            "url_route": scope.get("url_route"),
            "user_id": getattr(scope.get("user"), "id", None),
        }

    def on_connect(self):
        """helper method for when a user connects, to log the session and participant information."""

        # 1. Force evaluate the lazy object to get the real object wrapper
        user_instance = self.scope["user"]._wrapped
        # 2. Check if the user is logged in
        if user_instance and user_instance.is_authenticated:
            self.db_user = user_instance
        else:
            self.db_user = None  # Assigns NULL in the database for anonymous sessions, helps with participant tracking and debugging.

        # if this is the publisher, we can log that they connected.
        if self.can_publish:
            try:
                self.active_session = LiveLocationSession.objects.create(
                    user=self.db_user,
                    room_name=self.room_name,
                )
                # then change their is streaming status to true
                self.db_user.is_streaming = True
                self.db_user.save(
                    update_fields=["is_streaming"]
                )  # Skips Unnecessary Database Triggers and only updates the is_streaming field in the database, improving performance and reducing overhead.
            except Exception as e:
                print(
                    f"Error creating LiveLocationSession: {e}: This is most likely because the session already exists. The publisher should not connect twice."
                )
        # if this is a viewer, we can log that they connected.
        else:
            try:
                self.active_participant = SessionParticipant.objects.create(
                    session=LiveLocationSession.objects.get(id=self.active_session.id),
                    user=self.db_user,
                    ip=self.get_real_ip(self.scope),
                    metadata=self.serialize_scope(dict(self.scope)),
                )
            except Exception as e:
                print(
                    f"Error creating SessionParticipant: {e}: This is most likely because the session does not exist yet. The publisher should connect first."
                )

        print("connect")

    def on_disconnect(self):
        """helper method for when a user disconnects, to log the session and participant information."""
        # if this is the publisher, we can log that they disconnected.
        if self.can_publish:
            try:
                # TODO: Consider using timezone-aware datetime objects for consistency
                self.active_session.ended_at = timezone.now()
                self.active_session.save()
                self.db_user.is_streaming = False
                self.db_user.save(
                    update_fields=["is_streaming"]
                )  # Skips Unnecessary Database Triggers and only updates the is_streaming field in the database, improving performance and reducing overhead.
            except LiveLocationSession.DoesNotExist:
                print("Warning: Attempted to end a session that does not exist.")
                pass  # Handle the case where the session does not exist

        else:
            try:
                self.active_participant.left_at = timezone.now()
                self.active_participant.save()
            except SessionParticipant.DoesNotExist:
                print("Warning: Attempted to end a participant that does not exist.")
                pass  # Handle the case where the participant does not exist

        print("disconnect")
