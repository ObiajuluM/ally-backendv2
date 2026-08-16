"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

# from chat.AI.action import appropriate_response_from_text

#
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()


from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
from livelocation.middleware import JwtAuthMiddlewareStack
from livelocation.routing import websocket_urlpatterns

# For websockets, we support both session auth and JWT-based auth so the
# consumer can identify publishers from browser or mobile clients.
websocket_application = JwtAuthMiddlewareStack(
    URLRouter(
        # Think of these as the websocket URLs Django Channels is allowed to answer.
        websocket_urlpatterns
    )
)


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": (
            # In local development, VS Code webviews may send an Origin header that
            # does not match 127.0.0.1, so we skip the origin check in DEBUG mode.
            # Outside DEBUG, keep the host/origin safety check in place.
            websocket_application
            if settings.DEBUG
            else AllowedHostsOriginValidator(websocket_application)
        ),
    }
)


# print(appropriate_response_from_text("my chest is paining me"))
