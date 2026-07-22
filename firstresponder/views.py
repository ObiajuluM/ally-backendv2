from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q, IntegerField

from django.contrib.postgres.search import (
    SearchHeadline,
    SearchQuery,
    SearchRank,
    SearchVector,
)
from django.db.models import (
    Case,
    Exists,
    OuterRef,
    Value,
    When,
)

from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config import settings
from firstresponder.models import (
    FirstResponder,
    FirstResponderType,
)
from firstresponder.serializers import FirstResponderSerializer
from servicearea.models import ServiceArea

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def get_user_point(lat, lng):
    """
    Convert user supplied coordinates into a PostGIS Point.

    PostGIS expects longitude first:
        Point(longitude, latitude)
    """
    return Point(
        float(lng),
        float(lat),
        # srid=4326,
    )


def validate_coordinates(lat, lng):
    """
    Validate latitude and longitude values.
    """

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return None

    if not (-90 <= lat <= 90):
        return None

    if not (-180 <= lng <= 180):
        return None

    return lat, lng


def apply_search(queryset, search_term):
    """
    Apply PostgreSQL full text search.

    Searchable fields:
        - name
        - description
        - firstresponder_type
        - organization_type

    Ranking priority:
        name > description > categories
    """

    vector = (
        SearchVector(
            "name",
            weight="A",
        )
        + SearchVector(
            "description",
            weight="B",
        )
        + SearchVector(
            "firstresponder_type",
            weight="C",
        )
        + SearchVector(
            "organization_type",
            weight="C",
        )
    )

    query = SearchQuery(search_term)
    # for raw OR searches: This gives you complete control, You can use operators.
    # query = SearchQuery(
    #     " | ".join(search_term).split(),
    #     search_type="raw",
    # )
    # For web-like searches
    # query = SearchQuery(
    #     search_term,
    #     search_type="websearch",
    # )

    return queryset.annotate(
        search_rank=SearchRank(
            vector,
            query,
        ),
        search_headline=SearchHeadline(
            "description",
            query,
        ),
    ).filter(
        search_rank__gt=0,
    )


def apply_geo_filter(queryset, user_point):
    """
    Apply PostGIS based responder discovery.

    Priority:
        1. Responders whose service area contains the user.
        2. Responders whose registered location is within 10km.

    We annotate instead of doing Python loops.
    """

    matching_service_area = ServiceArea.objects.filter(
        polygon__contains=user_point,
        first_responders=OuterRef("pk"),
    )

    queryset = queryset.annotate(
        in_service_area=Exists(matching_service_area),
        distance=Distance(
            "address__location",
            user_point,
        ),
    )

    return queryset.filter(Q(in_service_area=True) | Q(distance__lte=D(km=10)))


# -------------------------------------------------------------------
# Views
# -------------------------------------------------------------------


class FirstResponderListView(ListAPIView):
    """
    List first responders.

    Supported queries:

        Search:
            ?search=police

        Geo:
            ?lat=6.52&lng=3.37

        Search + Geo:
            ?search=hospital&lat=6.52&lng=3.37

        Type + Geo:
            ?type=lawenforcement&lat=6.52&lng=3.37
    """

    serializer_class = FirstResponderSerializer

    def get_permissions(self):
        if not settings.DEBUG:
            self.permission_classes = [
                IsAuthenticated,
            ]
        return super().get_permissions()

    def get_queryset(self):

        queryset = FirstResponder.objects.select_related(
            "address",
        ).prefetch_related(
            "service_areas",
        )

        search = self.request.query_params.get("search")

        responder_type = self.request.query_params.get("type")

        lat = self.request.query_params.get("lat")

        lng = self.request.query_params.get("lng")

        # -------------------------------------------------------------
        # No filters supplied
        # Return empty response instead of all responders
        # REMEMBER: the below return was emptied out to avoid scrapers-------------------------------------------------------------

        if not settings.DEBUG:
            if not search and not responder_type and not (lat and lng):
                return FirstResponder.objects.none()

        # -------------------------------------------------------------
        # Type filtering
        # -------------------------------------------------------------

        if responder_type:

            if responder_type not in FirstResponderType.values:
                return FirstResponder.objects.none()

            queryset = queryset.filter(firstresponder_type=responder_type)

        # -------------------------------------------------------------
        # Keyword search
        # -------------------------------------------------------------

        if search:
            queryset = apply_search(
                queryset,
                search,
            )

        # -------------------------------------------------------------
        # Geo filtering
        # -------------------------------------------------------------

        if lat and lng:

            coordinates = validate_coordinates(
                lat,
                lng,
            )

            if not coordinates:
                return FirstResponder.objects.none()

            lat, lng = coordinates

            user_point = get_user_point(
                lat,
                lng,
            )

            queryset = apply_geo_filter(
                queryset,
                user_point,
            )

        # -------------------------------------------------------------
        # Ranking
        # -------------------------------------------------------------

        if lat and lng:
            queryset = queryset.annotate(
                service_priority=Case(
                    When(
                        in_service_area=True,
                        then=Value(1),
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )

        if search and lat and lng:

            queryset = queryset.order_by(
                "-service_priority",
                "-search_rank",
                "distance",
            )

        elif search:

            queryset = queryset.order_by(
                "-search_rank",
                "name",
            )
        # if search:
        #     queryset = queryset.order_by(
        #         "-service_priority",
        #         "-search_rank",
        #         "distance",
        #     )

        # elif lat and lng:
        #     queryset = queryset.order_by(
        #         "-service_priority",
        #         "distance",
        #     )

        else:

            queryset = queryset.order_by("name")

        return queryset

    def list(self, request, *args, **kwargs):

        queryset = self.get_queryset()

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class FirstResponderRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):  #
    """
    Retrieve a single responder.

    Creation/update/delete are disabled currently
    to match your previous API behavior.
    """

    queryset = FirstResponder.objects.select_related(
        "address",
    ).prefetch_related(
        "service_areas",
    )

    serializer_class = FirstResponderSerializer

    http_method_names = [
        "get",
        "head",
        "options",
    ]
