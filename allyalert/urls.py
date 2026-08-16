from django.urls import path
from allyalert.views import (
    AlertDeliveryRetrieveUpdateView,
    AlertReportListCreateView,
    AllyAlertListCreateView,
    AllyAlertRetrieveUpdateDestroyView,
)

urlpatterns = [
    path("", AllyAlertListCreateView.as_view(), name="ally-alert-list-create"),
    path(
        "<uuid:pk>/",
        AllyAlertRetrieveUpdateDestroyView.as_view(),
        name="ally-alert-retrieve-update-destroy",
    ),
    path(
        "delivery/<uuid:pk>/",
        AlertDeliveryRetrieveUpdateView.as_view(),
        name="ally-alert-delivery-retrieve-update",
    ),
    path(
        "report/",
        # "report/<uuid:pk>/",
        AlertReportListCreateView.as_view(),
        name="ally-alert-delivery-retrieve-update",
    ),
]
