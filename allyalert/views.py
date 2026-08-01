from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.utils import timezone

from ally.views import IsOwner

from allyalert.models import AlertDelivery, AlertReport, AllyAlert
from allyalert.serializers import (
    AlertDeliverySerializer,
    AlertReportSerializer,
    AllyAlertSerializer,
)
from config import settings


class AllyAlertListCreateView(ListCreateAPIView):
    serializer_class = AllyAlertSerializer
    queryset = AllyAlert.objects.select_related("creator").order_by("-created_at")

    def get_permissions(self):
        if not settings.DEBUG:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        if request.query_params.get("mine", "").lower() == "true":
            queryset = (
                AllyAlert.objects.filter(creator=request.user)
                .select_related("creator")
                .order_by("-created_at")
            )
        else:
            # TODO: make location based filtering for alerts, so that users only see alerts relevant to their location.
            queryset = (
                AllyAlert.objects.filter(status=AllyAlert.Status.ACTIVE)
                .select_related("creator")
                .order_by("-created_at")
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        # Bind the authenticated user as the creator so clients
        # cannot spoof a different creator in the request body.
        serializer.save(creator=self.request.user)


class AllyAlertRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    """
    GET    /v1/alerts/<id>/  — retrieve a single alert (any authenticated user)
    PATCH  /v1/alerts/<id>/  — partial update          (creator only)
    PUT    /v1/alerts/<id>/  — full update             (creator only)
    DELETE /v1/alerts/<id>/  — soft-delete             (creator only)
    """

    serializer_class = AllyAlertSerializer
    # queryset = AllyAlert.objects.select_related("creator")
    # Filter the queryset to only include ACTIVE statuses
    queryset = AllyAlert.objects.filter(status=AllyAlert.Status.ACTIVE).select_related(
        "creator"
    )

    def get_permissions(self):
        # In production, mutating methods (PUT, PATCH, DELETE) require the
        # requester to own the object. In DEBUG mode the check is skipped to
        # make local testing easier without having to fake ownership.
        if not settings.DEBUG:
            if self.request.method in ("PUT", "PATCH", "DELETE"):
                self.permission_classes = [IsAuthenticated, IsOwner]
            else:
                self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        # Soft-delete: set status to REMOVED instead of dropping the row.
        # This keeps delivery and report records intact and allows auditing.
        instance = self.get_object()
        instance.status = AllyAlert.Status.REMOVED
        instance.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AlertDeliveryRetrieveUpdateView(RetrieveUpdateDestroyAPIView):
    """
    PATCH  /v1/delivery/<id>/
        Mark the delivery as viewed.
    """

    serializer_class = AlertDeliverySerializer
    http_method_names = ["patch"]
    # queryset = AlertDelivery.objects.select_related(
    #     "alert",
    #     "user",
    # )

    def get_permissions(self):
        if not settings.DEBUG:
            self.permission_classes = [IsAuthenticated, IsOwner]
        return super().get_permissions()

    def get_queryset(self):
        if not settings.DEBUG:
            return AlertDelivery.objects.filter(user=self.request.user).select_related(
                "alert", "user"
            )
        return AlertDelivery.objects.select_related("alert", "user")

    def patch(self, request, *args, **kwargs):
        """"""
        delivery = self.get_object()
        if delivery.viewed_at is None:
            delivery.viewed_at = timezone.now()
            delivery.save(update_fields=["viewed_at"])
        serializer = self.get_serializer(delivery)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AlertReportListCreateView(ListCreateAPIView):
    """
    For creating alert reports and listing all reports. Only authenticated users can create reports, no such thing as viewing reports.
    GET  /v1/alert-reports/         — list all reports, newest first
    POST /v1/alert-reports/         — create a new report
    """

    serializer_class = AlertReportSerializer

    def get_permissions(self):
        if not settings.DEBUG:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        """Make sure to only return reports for ACTIVE alerts, so that users cannot see reports for removed or expired alerts."""
        return (
            AlertReport.objects.filter(alert__status=AllyAlert.Status.ACTIVE)
            .select_related("reporter", "alert")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        # Bind the authenticated user as the reporter so clients
        # cannot spoof a different reporter in the request body.
        # TODO: Add logic to increment the report_count or helpful_count  on the associated AllyAlert instance when a new report is created. This will help track the number of reports for each alert.
        serializer.save(reporter=self.request.user)
        # get alert instance from the serializer and increment either the helpful_count or report_count based on the alert report reason. This will help track the number of reports for each alert.
        alert = serializer.validated_data["alert"]

        if serializer.validated_data["reason"] == AlertReport.Reason.HELPFUL:
            alert.helpful_count.append(self.request.user.id)
            field_to_update = "helpful_count"
        else:
            alert.report_count.append(self.request.user.id)
            field_to_update = "helpful_count"
        # Force Django to save the specific modified field
        alert.save(update_fields=[field_to_update])
