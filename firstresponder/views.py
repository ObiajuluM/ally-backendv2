from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from config import settings

from rest_framework.response import Response
from rest_framework import status
import math
import re

from firstresponder.models import FirstResponder, FirstResponderType
from firstresponder.serializers import FirstResponderSerializer

# for permissions to decorate views


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
    """Ray-casting algorithm. polygon is a list of [lng, lat] pairs (GeoJSON order).

    Imagine standing at a point and shooting a ray in one direction.
    Count how many times that ray crosses the edges of the shape.
    Odd number of crossings = you're INSIDE. Even = you're OUTSIDE.
    """
    n = len(polygon)
    inside = False
    j = n - 1  # start by comparing the last edge to the first point
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]  # xi=lng, yi=lat  (GeoJSON [lng, lat])
        xj, yj = polygon[j][0], polygon[j][1]  # xj=lng, yj=lat
        # Check if the ray from our point crosses this edge.
        if ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / (yj - yi) + xi
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


# --------------------------------------------------------------------------
# SEARCH HELPERS
# Tools for turning a raw user query into clean, matchable tokens.
# --------------------------------------------------------------------------

_STOP_WORDS = settings.STOP_WORDS


def _tokenize(text):
    """Split text into a set of lower-cased tokens with stop words removed.

    Example:  "The police are abusive"
              → words:    ["the", "police", "are", "abusive"]
              → no stops: {"police", "abusive"}

    Words are matched exactly (no stemming), so "hospital" will NOT match
    "hospitals" — the search term must match the stored text as written.
    """
    # Split on any non-letter character (spaces, punctuation, numbers).
    words = re.split(r"[^a-z]+", text.lower())
    return {w for w in words if w and w not in _STOP_WORDS}


def _relevance_score(responder, query):
    """Score how relevant a first responder is to a free-text search query.

    The query is first broken into tokens (see _tokenize), so:
      - Filler words are ignored: "the police are abusive" → {"police", "abusive"}
      - Each meaningful word is matched exactly and scored independently, then summed.
      - Matching is case-insensitive but NOT stemmed, so "hospitals" will only
        match "hospitals", not "hospital".

    Points per token match:
      - NAME contains the token        → +3  (strongest signal)
      - TYPE contains the token        → +2
      - DESCRIPTION contains the token → +1
      - Any TAG contains the token     → +1 per tag

    Returns the total integer score across all tokens (0 = nothing matched).
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        # Query was all stop words or empty — treat everything as equally relevant.
        return 1

    score = 0

    # Pre-tokenize each responder field once so we're not re-stemming inside the loop.
    name_tokens = _tokenize(responder.name or "")
    type_tokens = _tokenize(responder.firstresponder_type or "")
    desc_tokens = _tokenize(responder.description or "")
    tag_token_sets = [_tokenize(tag) for tag in (responder.tags or [])]

    for token in query_tokens:
        # +3 if this search word appears in the responder's name.
        if token in name_tokens:
            score += 3

        # +2 if it appears in the responder's category type.
        if token in type_tokens:
            score += 2

        # +1 if it appears anywhere in the description.
        if token in desc_tokens:
            score += 1

        # +1 for every tag that contains this word.
        for tag_tokens in tag_token_sets:
            if token in tag_tokens:
                score += 1

    return score


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
    # Start with no winner yet — like saying "I haven't found the closest one yet."
    best = None
    for polygon in service_areas:
        if len(polygon) < 3 or not _point_in_polygon(lat, lng, polygon):
            continue
        # GeoJSON [lng, lat]: index 0 = lng, index 1 = lat
        c_lng = sum(p[0] for p in polygon) / len(polygon)
        c_lat = sum(p[1] for p in polygon) / len(polygon)
        d = _haversine_km(lat, lng, c_lat, c_lng)
        # If this is the first shape we've checked, or it's closer than the previous winner,
        # it becomes the new winner — like keeping track of the shortest straw.
        if best is None or d < best:
            best = d
    # Give back the distance to the closest shape's center (or None if the user wasn't inside any).
    return best


# --------------------------------------------------------------------------
# FIRST RESPONDER VIEWS
# --------------------------------------------------------------------------


# REMEMBER: service_areas polygons use GeoJSON coordinate order: [lng, lat]: longitude and latitude not the usual (lat, lng) order. This is a common source of confusion, so be careful!
# Do NOT store or pass [lat, lng] — the point-in-polygon math depends on this order.
# TODO: add a fix so search goes wider and ignores location: this may require some UI changes
class FirstResponderListCreateView(ListCreateAPIView):
    # select_related("address") fetches the linked address in the same DB query
    # instead of making a separate query for each responder (much faster).
    queryset = FirstResponder.objects.select_related(
        "address",
    )
    serializer_class = FirstResponderSerializer
    # POST (create) is disabled — first responders are managed by admins only.
    http_method_names = ["get", "head", "options"]

    def get_permissions(self):
        if not settings.DEBUG:
            # if self.request.method == "GET":
            self.permission_classes = [
                # IsOwner,
                IsAuthenticated,
            ]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        # Read the optional query parameters from the URL.
        # Supported combinations:
        #   ?search=police                          — keyword search only
        #   ?lat=6.52&lng=3.37                      — geo filter only
        #   ?lat=6.52&lng=3.37&type=lawenforcement  — geo + type filter
        #   ?search=hospital&lat=6.52&lng=3.37      — keyword search + geo
        #   ?search=hospital&lat=6.52&lng=3.37&type=firstaidandmedical — all three
        lat_param = request.query_params.get("lat")
        lng_param = request.query_params.get("lng")
        type_param = request.query_params.get("type")
        # search_param is a free-text keyword the frontend can pass to find relevant responders.
        # e.g. "police", "hospital", "flood", "domestic violence"
        search_param = request.query_params.get("search", "").strip()

        # If a type filter was given, make sure it's one of the four valid types.
        if type_param is not None and type_param not in FirstResponderType.values:
            return Response(
                {
                    "error": f"Invalid type '{type_param}'. Valid values are: {', '.join(FirstResponderType.values)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── NO GEO PARAMS ────────────────────────────────────────────────────
        # If neither lat nor lng was provided, return a plain list sorted by relevance to the search term (if given), otherwise unsorted.
        if lat_param is None and lng_param is None:
            qs = self.get_queryset()
            if type_param is not None:
                qs = qs.filter(firstresponder_type=type_param)

            if search_param:
                # Score every responder and discard ones with zero relevance.
                # Sort descending so the most relevant appears first.
                scored = [(r, _relevance_score(r, search_param)) for r in qs]
                scored = [(r, s) for r, s in scored if s > 0]
                scored.sort(key=lambda x: x[1], reverse=True)
                serializer = self.get_serializer([r for r, _ in scored], many=True)
            else:
                serializer = self.get_serializer(qs, many=True)

            # return Response(serializer.data)
            # REMEMBER: the above return was emptied out to avoid scrapers
            return (
                Response(serializer.data)
                if settings.DEBUG
                else Response(status=status.HTTP_204_NO_CONTENT)
            )

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
        # We build two separate lists, then join them so zone matches always
        # appear BEFORE radius matches in the final response.
        #
        # Tier 0 — Zone matches:
        #   The user is physically inside one of this responder's service-area
        #   polygons. These are the most directly relevant results.
        #   Sort key: distance to the matched zone's centroid (closest zone first).
        #
        # Tier 1 — Radius fallback:
        #   No custom zones defined (or the user isn't inside any of them),
        #   but the responder's registered address is within 10 km.
        #   These are appended after all zone matches.
        #   Sort key: straight-line distance to the responder's address.
        zone_matches = []  # tier 0
        radius_matches = []  # tier 1

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
                # Check if the user is standing inside any of those zones.
                zone_dist = _nearest_zone_distance_km(
                    center_lat, center_lng, r.service_areas
                )
                if zone_dist is not None:
                    # User is inside a zone — tier 0 (highest priority).
                    zone_matches.append((r, zone_dist))
                elif dist <= 10.0:
                    # User is NOT in any zone, but the responder's address is
                    # within 10 km — still useful, just lower priority.
                    radius_matches.append((r, dist))
            else:
                # No custom zones at all — fall back to 10 km radius rule.
                if dist <= 10.0:
                    radius_matches.append((r, dist))

        # Tag each entry with its tier (0 = zone match, 1 = radius fallback)
        # so the sort can keep them in the right order later.
        nearby = [(r, dist, 0) for r, dist in zone_matches] + [
            (r, dist, 1) for r, dist in radius_matches
        ]

        # ── SEARCH FILTERING & SCORING (geo path) ───────────────────────────
        # If a search term was given, discard responders with zero relevance
        # and attach a relevance score to each remaining one.
        # Tuples become (responder, distance_km, tier, relevance_score).
        if search_param:
            scored_nearby = []
            for r, dist, tier in nearby:
                score = _relevance_score(r, search_param)
                if score > 0:
                    scored_nearby.append((r, dist, tier, score))
            nearby_with_scores = scored_nearby
        else:
            # No search term — every responder gets a neutral score of 0.
            # Sorting will fall back to tier, then distance.
            nearby_with_scores = [(r, dist, tier, 0) for r, dist, tier in nearby]

        # ── GROUPING & SORTING ───────────────────────────────────────────────
        # Organise results into four "buckets", one per responder type.
        # If a type filter was given, we only fill that one bucket.
        active_types = (
            [type_param] if type_param is not None else list(FirstResponderType.values)
        )
        buckets = {ft: [] for ft in active_types}
        for r, dist, tier, score in nearby_with_scores:
            ft = r.firstresponder_type
            if ft in buckets:
                buckets[ft].append((r, dist, tier, score))

        # Build the final response dict.
        # Sort key: tier first (zone matches before radius), then highest relevance
        # score, then closest distance. This guarantees:
        #   1. Responders whose zone the user is inside → always listed first.
        #   2. Within each tier, more relevant results rank above less relevant ones.
        #   3. Equal relevance → closer responder wins.
        result = {}
        for ft, items in buckets.items():
            items.sort(key=lambda x: (x[2], -x[3], x[1]))  # (tier, -score, distance)
            serialized = []
            for r, dist, tier, score in items:
                data = FirstResponderSerializer(r, context={"request": request}).data
                data["distance_km"] = round(dist, 3)  # how far the zone/address is
                if search_param:
                    data["relevance_score"] = (
                        score  # expose score so frontend can use it
                    )
                serialized.append(data)
            result[ft] = serialized

        return Response(result)


class FirstResponderRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    # Standard detail view: GET, PUT, PATCH, DELETE a single first responder by its UUID.
    queryset = FirstResponder.objects.select_related(
        "address",
    )
    serializer_class = FirstResponderSerializer
