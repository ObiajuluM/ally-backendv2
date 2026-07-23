from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class AllyJWTAuthentication(JWTAuthentication):
    """Custom JWT authentication class that checks if the user is active (not blocked)."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        if not user.is_active:
            raise AuthenticationFailed(
                "Your account has been disabled, contact support.",
                code=status.HTTP_403_FORBIDDEN,
            )

        return user
