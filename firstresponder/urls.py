from django.urls import path

from firstresponder.views import (
    FirstResponderListCreateView,
    FirstResponderRetrieveUpdateDestroyView,
)

urlpatterns = [
    path(
        "",
        FirstResponderListCreateView.as_view(),
        name="firstresponder-list-create",
    ),
    path(
        "<uuid:pk>/",
        FirstResponderRetrieveUpdateDestroyView.as_view(),
        name="firstresponder-retrieve-update-destroy",
    ),
]
