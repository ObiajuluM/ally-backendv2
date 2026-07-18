from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections

from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def get_user_from_token(raw_token):
    # Reuse SimpleJWT's validation logic so websocket auth matches HTTP auth.
    authenticator = JWTAuthentication()
    validated_token = authenticator.get_validated_token(raw_token)
    return authenticator.get_user(validated_token)


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Drop stale DB connections before resolving a user for this socket.
        close_old_connections()

        # Allow websocket clients to authenticate with a JWT instead of a session.
        raw_token = self.get_token_from_scope(scope)
        if raw_token:
            try:
                # Replace the anonymous/session user with the JWT-authenticated user.
                scope["user"] = await get_user_from_token(raw_token)
            except Exception:
                # Invalid or expired tokens fall back to an anonymous websocket user.
                scope["user"] = AnonymousUser()
        else:
            # Keep the connection anonymous when no token is provided.
            scope.setdefault("user", AnonymousUser())

        return await super().__call__(scope, receive, send)

    def get_token_from_scope(self, scope):
        # Prefer a standard Authorization header when the client can send one.
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()
        if auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()

        # Fallback for browser clients that can only send the token in the URL.
        query_params = parse_qs(scope.get("query_string", b"").decode())
        return query_params.get("token", [None])[0]


def JwtAuthMiddlewareStack(inner):
    # Run Django's default auth stack first, then let JWT auth override the user.
    return AuthMiddlewareStack(JwtAuthMiddleware(inner))
