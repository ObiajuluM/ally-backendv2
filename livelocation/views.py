# TODO: a away to modify if the user is streaming -- so i can use it to verify if the user is streaming or not for the frontend streemaing page

from rest_framework import status

from ally.models import User
from ally.views import IsOwner
from config import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import (
    get_user_model,
)  # use this to get the user model instead of "from django.contrib.auth.models import User"

# 1. Grab the correct model class dynamically
# User = get_user_model()


class UserIsStreamingView(APIView):
    """Checks if a particular user is streaming."""

    def get_permissions(self):
        if not settings.DEBUG:
            # if self.request.method == "GET":
            self.permission_classes = [
                IsOwner,
                IsAuthenticated,
            ]
        return super().get_permissions()

    def get(self, request, *args, **kwargs):
        user_param = request.query_params.get("uid")

        try:
            # Check if user exists
            user = get_object_or_404(User, pk=user_param)
            return Response(
                {"is_streaming": user.is_streaming}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
