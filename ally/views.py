from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from config import settings
from .models import MyInformation, User, UserDevice
from .serializers import (
    MyInformationSerializer,
    UserSerializer,
)
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests

# from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

# for permissions to decorate views

from rest_framework.permissions import BasePermission

# --------------------------------------------------------------------------
# PERMISSIONS
# Think of permissions like a bouncer at a door.
# Before letting anyone in, the bouncer checks if they're allowed.
# --------------------------------------------------------------------------


class APIPermission(BasePermission):
    # By default, this bouncer does NOT let read-only requests through automatically.
    allow_read_only = False

    @staticmethod
    def is_safe(request):
        # "Safe" methods are ones that only look at data, never change it.
        # GET = read a page, HEAD = check if a page exists, OPTIONS = ask what's allowed.
        return request.method in ["GET", "HEAD", "OPTIONS"]


class IsOwner(APIPermission):
    def has_object_permission(self, request, view, obj):
        # Only let someone touch a piece of data if it belongs to them.
        # Like: you can only edit YOUR profile, not someone else's.
        return request.user and obj.owner == request.user


# --------------------------------------------------------------------------
# GOOGLE AUTHENTICATION
# This is the front door for users who sign in with their Google account.
# --------------------------------------------------------------------------


class GoogleAuthView(APIView):
    def post(self, request):
        try:
            # Grab the Google ID token the app sent us.
            # A token is like a signed letter from Google saying "yes, this is really them".
            token = request.data.get("id_token")
            if not token:
                return Response(
                    {"error": "ID token not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Ask Google to verify the token is genuine and hasn't been tampered with.
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )

            email = idinfo["email"]
            name = idinfo.get("name", "")

            # Look up the user by email.
            # If they've never logged in before, create a brand-new account for them.
            # get_or_create returns (user_object, True/False) — True means it was just created.
            user, created = User.objects.get_or_create(
                email=email,
                # these defaults are only used when a new user is created;
                # if the user already exists, these values are ignored.
                defaults={
                    "email": email,
                    "username": name if name else "",
                },
            )

            # Only a brand-new user gets an initial MyInformation record here.
            # Returning users keep whatever profile is already linked to them.
            if created:
                user.my_information = MyInformation.objects.create(name=name)
                user.save(update_fields=["my_information"])

            # If a user has been banned or deactivated, we don't let them log in.
            if not user.is_active:
                return Response(
                    {"detail": "Your account has been disabled, contact support."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Give the user a JWT (JSON Web Token) — like a temporary pass/wristband
            # that proves who they are without needing to log in again on every request.
            # refresh = long-lived token to get new access tokens.
            # access  = short-lived token used on every API call.
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )
        except Exception as e:
            print(e)
            # import traceback
            # traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --------------------------------------------------------------------------
# MY INFORMATION VIEWS
# Endpoints for the user's personal/medical profile.
# --------------------------------------------------------------------------


class MyInformationListCreateView(ListCreateAPIView):
    # select_related("address") means: when fetching MyInformation rows,
    # also fetch the linked Address in the SAME database query (more efficient).
    queryset = MyInformation.objects.select_related("address").all()
    serializer_class = MyInformationSerializer


class MyInformationRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    serializer_class = MyInformationSerializer
    # You must be logged in AND own the object to use this endpoint.
    # permission_classes = [IsAuthenticated, IsOwner]
    # Only retrieve (GET) and update (PUT / PATCH) are permitted — delete is blocked.
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_permissions(self):
        if not settings.DEBUG:
            self.permission_classes = [IsOwner, IsAuthenticated]
        return super().get_permissions()

    def get_object(self):
        # Instead of looking up a profile by its ID in the URL,
        # we always return the profile that belongs to whoever is logged in.
        return self.request.user.my_information


# --------------------------------------------------------------------------
# USER VIEWS
# Endpoints for the user account itself (email, phone, username, etc.).
# --------------------------------------------------------------------------
class UserListCreateView(ListCreateAPIView):
    queryset = User.objects.select_related("my_information")
    serializer_class = UserSerializer


class UserRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.select_related("my_information")
    serializer_class = UserSerializer
    # Must be logged in. No IsOwner needed because get_object() already
    # forces the response to be the logged-in user's own data.
    # permission_classes = [IsAuthenticated, IsOwner]
    # Only retrieve (GET) and update (PUT / PATCH) are permitted — delete is blocked.
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_permissions(self):
        if not settings.DEBUG:
            # if self.request.method == "GET":
            self.permission_classes = [
                IsOwner,
                IsAuthenticated,
            ]
        return super().get_permissions()

    def get_object(self):
        # Always return the currently logged-in user's account.
        # No UUID in the URL is needed.
        # return self.queryset.get(pk="4dcfff31-16a6-4485-95c8-ed6ab6c53981")
        return self.request.user


class GeminidView(RetrieveUpdateDestroyAPIView):

    http_method_names = ["get"]
    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):
        return Response(
            {
                "model": settings.GEMINI_MODEL,
                "key": settings.GEMINI_API_KEY,
                "x": settings.X_URL,
                "website": settings.WEBSITE_URL,
                "whatsapp": settings.WHATSAPP_URL,
                "youtube": settings.YOUTUBE_PLAYLIST,
            }
        )


class RegisterFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("RegisterFCMTokenView called")
        fcm_token = request.data.get("fcm_token")
        platform = request.data.get("platform", "android")

        if not fcm_token:
            return Response(
                {"error": "fcm_token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Update or create device entry for the authenticated user
        device, created = UserDevice.objects.update_or_create(
            fcm_token=fcm_token, defaults={"user": request.user, "platform": platform}
        )

        return Response(
            {"message": "Token registered successfully", "created": created},
            status=status.HTTP_200_OK,
        )
