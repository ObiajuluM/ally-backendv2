from django.urls import path

from firstresponder.views import (
    FirstResponderListView,
    FirstResponderRetrieveUpdateDestroyView,
)

urlpatterns = [
    path(
        "",
        FirstResponderListView.as_view(),
        name="firstresponder-list-no-create",
    ),
    # path(
    #     "<uuid:pk>/",
    #     FirstResponderRetrieveUpdateDestroyView.as_view(),
    #     name="firstresponder-retrieve-update-destroy",
    # ),
]
