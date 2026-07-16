# urls for consumers
from django.urls import re_path
from .consumers import LiveLocationConsumer

# WebSocket URL patterns used by Django Channels.
websocket_urlpatterns = [
    # Matches paths like ws/live/<publisher-user-id>/ so viewers can subscribe
    # to a single publisher's room using that user's UUID.
    re_path(r"ws/live/(?P<room_name>[^/]+)/$", LiveLocationConsumer.as_asgi()),
]
