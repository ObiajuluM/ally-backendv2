from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from config import settings
from .models import FirstResponder, FirstResponderType, MyInformation, User
from .serializers import (
    FirstResponderSerializer,
    MyInformationSerializer,
    UserSerializer,
)
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests
import math

# from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

# for permissions to decorate views

from rest_framework.permissions import BasePermission


class APIPermission(BasePermission):
    allow_read_only = False

    @staticmethod
    def is_safe(request):
        return request.method in ["GET", "HEAD", "OPTIONS"]


class IsOwner(APIPermission):
    def has_object_permission(self, request, view, obj):
        return request.user and obj.owner == request.user


class GoogleAuthView(APIView):
    def post(self, request):
        try:
            token = request.data.get("id_token")
            if not token:
                return Response(
                    {"error": "ID token not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify token with Google
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )

            email = idinfo["email"]
            name = idinfo.get("name", "")

            # Get or create user, the created bool indicates if a new user was created or an existing one was found
            user, created = User.objects.get_or_create(
                email=email,
                # only used when a new user is created.If the user already exists, defaults does not update anything.
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

            # Issue JWT token
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MyInformationListCreateView(ListCreateAPIView):
    queryset = MyInformation.objects.select_related("address").all()
    serializer_class = MyInformationSerializer


class MyInformationRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    serializer_class = MyInformationSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    # Only retrieve (GET) and update (PUT / PATCH) are permitted — delete is blocked.
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_object(self):
        # Always resolve to the authenticated user's own MyInformation — no UUID in the URL needed.
        return self.request.user.my_information


class UserListCreateView(ListCreateAPIView):
    queryset = User.objects.select_related("my_information")
    # queryset = MyInformation.objects.prefetch_related("myInformation")
    serializer_class = UserSerializer


class UserRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.select_related("my_information")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    # Only retrieve (GET) and update (PUT / PATCH) are permitted — delete is blocked.

    http_method_names = ["get", "put", "patch", "head", "options"]


def _haversine_km(lat1, lon1, lat2, lon2):
    """Return the great-circle distance in km between two (lat, lon) points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class FirstResponderListCreateView(ListCreateAPIView):
    # use select_related() for instead of prefetch_related() to optimize queries
    # since we are dealing with a single related object (address)
    queryset = FirstResponder.objects.select_related(
        "address",
    )
    serializer_class = FirstResponderSerializer
    http_method_names = ["get", "head", "options"]

    def list(self, request, *args, **kwargs):
        lat_param = request.query_params.get("lat")
        lng_param = request.query_params.get("lng")
        type_param = request.query_params.get("type")

        # Validate type param when supplied.
        if type_param is not None and type_param not in FirstResponderType.values:
            return Response(
                {
                    "error": f"Invalid type '{type_param}'. Valid values are: {', '.join(FirstResponderType.values)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fall back to default list behaviour when no geo params are supplied.
        if lat_param is None and lng_param is None:
            qs = self.get_queryset()
            if type_param is not None:
                qs = qs.filter(firstresponder_type=type_param)
            serializer = self.get_serializer(qs, many=True)
            return Response(serializer.data)

        # Validate both params are present and numeric.
        if lat_param is None or lng_param is None:
            return Response(
                {"error": "Both 'lat' and 'lng' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            center_lat = float(lat_param)
            center_lng = float(lng_param)
        except ValueError:
            return Response(
                {"error": "'lat' and 'lng' must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        responders = (
            FirstResponder.objects.select_related("address")
            .exclude(address__isnull=True)
            .exclude(address__latitude__isnull=True)
            .exclude(address__longitude__isnull=True)
        )
        if type_param is not None:
            responders = responders.filter(firstresponder_type=type_param)

        # Compute distance and keep only those within 100 km.
        nearby = []
        for r in responders:
            dist = _haversine_km(
                center_lat,
                center_lng,
                float(r.address.latitude),
                float(r.address.longitude),
            )
            if dist <= 100.0:
                nearby.append((r, dist))

        # Group into buckets (only the requested type when filtered, else all four).
        active_types = (
            [type_param] if type_param is not None else list(FirstResponderType.values)
        )
        buckets = {ft: [] for ft in active_types}
        for r, dist in nearby:
            ft = r.firstresponder_type
            if ft in buckets:
                buckets[ft].append((r, dist))

        result = {}
        for ft, items in buckets.items():
            items.sort(key=lambda x: x[1])
            serialized = []
            for r, dist in items:
                data = FirstResponderSerializer(r, context={"request": request}).data
                data["distance_km"] = round(dist, 3)
                serialized.append(data)
            result[ft] = serialized

        return Response(result)


class FirstResponderRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    queryset = FirstResponder.objects.select_related(
        "address",
    )
    serializer_class = FirstResponderSerializer
