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
    permission_classes = [IsAuthenticated, IsOwner]
    # Only retrieve (GET) and update (PUT / PATCH) are permitted — delete is blocked.
    http_method_names = ["get", "put", "patch", "head", "options"]

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
    permission_classes = [IsAuthenticated]
    # Only retrieve (GET) and update (PUT / PATCH) are permitted — delete is blocked.
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_object(self):
        # Always return the currently logged-in user's account.
        # No UUID in the URL is needed.
        return self.request.user


# --------------------------------------------------------------------------
# GEO HELPER FUNCTIONS
# These are math tools used to work with locations on a map.
# --------------------------------------------------------------------------


def _haversine_km(lat1, lon1, lat2, lon2):
    """Return the great-circle distance in km between two (lat, lon) points."""
    # Imagine the Earth as a ball. This formula figures out the shortest
    # path along the surface of that ball between two GPS points.
    R = 6371.0  # Earth's mean radius in kilometres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)  # difference in latitudes
    dlambda = math.radians(lon2 - lon1)  # difference in longitudes
    # Haversine formula: a is the square of half the chord length between the points.
    # Don't worry about the maths — it's a well-known formula for spherical geometry.
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    # Angular distance in radians via atan2, then multiply by radius to get km.
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _point_in_polygon(lat, lng, polygon):
    """Ray-casting algorithm. polygon is a list of [lat, lng] pairs.

    Imagine standing at a point and shooting a ray in one direction.
    Count how many times that ray crosses the edges of the shape.
    Odd number of crossings = you're INSIDE. Even = you're OUTSIDE.
    """
    n = len(polygon)
    inside = False
    j = n - 1  # start by comparing the last edge to the first point
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]  # current polygon vertex
        xj, yj = polygon[j][0], polygon[j][1]  # previous polygon vertex
        # Check if the ray from our point crosses this edge.
        if ((yi > lng) != (yj > lng)) and (
            lat < (xj - xi) * (lng - yi) / (yj - yi) + xi
        ):
            # Each crossing flips inside/outside, like toggling a light switch.
            inside = not inside
        j = i  # move to the next edge
    return inside


def _in_any_service_area(lat, lng, service_areas):
    """Return True if (lat, lng) falls inside any of the responder's service area polygons.

    A responder can have MULTIPLE service areas (e.g. Abia AND Lagos).
    We check each one and return True as soon as we find a match.
    """
    for polygon in service_areas:
        # Need at least 3 points to form a real shape (a triangle is the minimum).
        if len(polygon) >= 3 and _point_in_polygon(lat, lng, polygon):
            return True
    # The user isn't inside any of the defined zones.
    return False


def _nearest_zone_distance_km(lat, lng, service_areas):
    """Return the distance (km) from (lat, lng) to the centroid of the closest
    matched service-area polygon.

    The centroid is the average of all the polygon's corner points — basically
    the 'middle' of the zone. We use this as the sort key so that when the user
    is inside multiple responders' zones, the one whose zone-centre is nearest
    appears first (most relevant).

    Only polygons that actually contain the point are considered.
    Returns None if the point isn't inside any polygon.
    """
    best = None
    for polygon in service_areas:
        if len(polygon) < 3 or not _point_in_polygon(lat, lng, polygon):
            continue
        # Centroid = average latitude and average longitude of all vertices.
        c_lat = sum(p[0] for p in polygon) / len(polygon)
        c_lng = sum(p[1] for p in polygon) / len(polygon)
        d = _haversine_km(lat, lng, c_lat, c_lng)
        if best is None or d < best:
            best = d
    return best


# --------------------------------------------------------------------------
# FIRST RESPONDER VIEWS
# --------------------------------------------------------------------------


class FirstResponderListCreateView(ListCreateAPIView):
    # select_related("address") fetches the linked address in the same DB query
    # instead of making a separate query for each responder (much faster).
    queryset = FirstResponder.objects.select_related(
        "address",
    )
    serializer_class = FirstResponderSerializer
    # POST (create) is disabled — first responders are managed by admins only.
    http_method_names = ["get", "head", "options"]

    def list(self, request, *args, **kwargs):
        # Read the optional query parameters from the URL.
        # e.g. /first-responders/?lat=6.52&lng=3.37&type=lawenforcement
        lat_param = request.query_params.get("lat")
        lng_param = request.query_params.get("lng")
        type_param = request.query_params.get("type")

        # If a type filter was given, make sure it's one of the four valid types.
        if type_param is not None and type_param not in FirstResponderType.values:
            return Response(
                {
                    "error": f"Invalid type '{type_param}'. Valid values are: {', '.join(FirstResponderType.values)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        #TODO  MAY Remove to avoid scrapers
        # ── NO GEO PARAMS ────────────────────────────────────────────────────
        # If neither lat nor lng was provided, just return a plain list
        # (optionally filtered by type). No distance sorting, no radius.
        if lat_param is None and lng_param is None:
            qs = self.get_queryset()
            if type_param is not None:
                qs = qs.filter(firstresponder_type=type_param)
            serializer = self.get_serializer(qs, many=True)
            return Response(serializer.data)

        # ── GEO PARAMS PROVIDED ──────────────────────────────────────────────
        # Both lat AND lng must be given together — one without the other is an error.
        if lat_param is None or lng_param is None:
            return Response(
                {"error": "Both 'lat' and 'lng' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            # Convert the URL strings ("6.52") into actual decimal numbers.
            center_lat = float(lat_param)
            center_lng = float(lng_param)
        except ValueError:
            return Response(
                {"error": "'lat' and 'lng' must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only consider responders that actually have a location stored.
        # Ones with no address at all are skipped — we can't place them on a map.
        responders = (
            FirstResponder.objects.select_related("address")
            .exclude(address__isnull=True)
            .exclude(address__latitude__isnull=True)
            .exclude(address__longitude__isnull=True)
        )
        # Narrow down to a specific type if the caller asked for one.
        if type_param is not None:
            responders = responders.filter(firstresponder_type=type_param)

        # ── DISTANCE / ZONE FILTERING ────────────────────────────────────────
        # Go through every responder and decide whether to include them.
        nearby = []
        for r in responders:
            # Calculate how far this responder is from the user's location (in km).
            dist = _haversine_km(
                center_lat,
                center_lng,
                float(r.address.latitude),
                float(r.address.longitude),
            )
            if r.service_areas:
                # This responder has custom service zones drawn on the map.
                # Include them only if the user is inside one of those zones.
                # Use the distance to the matched zone's centroid for sorting
                # (not the distance to the responder's address), so the zone
                # whose centre is closest to the user sorts first.
                zone_dist = _nearest_zone_distance_km(
                    center_lat, center_lng, r.service_areas
                )
                if zone_dist is not None:
                    nearby.append((r, zone_dist))
            else:
                # No custom zones — use the default rule: within 200 km.
                if dist <= 200.0:
                    nearby.append((r, dist))

        # ── GROUPING & SORTING ───────────────────────────────────────────────
        # Organise results into four "buckets", one per responder type.
        # If a type filter was given, we only fill that one bucket.
        active_types = (
            [type_param] if type_param is not None else list(FirstResponderType.values)
        )
        buckets = {ft: [] for ft in active_types}
        for r, dist in nearby:
            ft = r.firstresponder_type
            if ft in buckets:
                buckets[ft].append((r, dist))

        # Build the final response dict.
        # Each bucket is sorted closest-first, and every item gets a distance_km field.
        result = {}
        for ft, items in buckets.items():
            items.sort(key=lambda x: x[1])  # sort by distance (smallest first)
            serialized = []
            for r, dist in items:
                data = FirstResponderSerializer(r, context={"request": request}).data
                data["distance_km"] = round(dist, 3)  # attach the distance in km
                serialized.append(data)
            result[ft] = serialized

        return Response(result)


class FirstResponderRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    # Standard detail view: GET, PUT, PATCH, DELETE a single first responder by its UUID.
    queryset = FirstResponder.objects.select_related(
        "address",
    )
    serializer_class = FirstResponderSerializer
