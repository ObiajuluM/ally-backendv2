import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


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

        # Cache the publish permission once on connect so receive() can make a
        # quick decision for every incoming socket message.
        self.can_publish = self.user_can_publish()

        # Every socket in the same room joins the same channel-layer group, which
        # lets one published update fan out to every connected viewer.
        self.room_group_name = f"live_{self.room_name}"
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )

        # The connection itself stays public so anonymous users can still watch.
        self.accept()

    def disconnect(self, close_code):
        # Remove this socket from the room group so it stops receiving broadcasts.
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    def receive(self, text_data):
        # Receiving from the socket means the client is trying to publish. 
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

    def user_can_publish(self):
        # A client may publish only when it is authenticated and connected to the
        # room named after that user's UUID.
        user = self.scope.get("user")
        return bool(user and user.is_authenticated and str(user.id) == self.room_name)
