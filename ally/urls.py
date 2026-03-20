from django.urls import path
from ally.views import (
    FirstResponderListCreateView,
    FirstResponderRetrieveUpdateDestroyView,
    GoogleAuthView,
    MyInformationListCreateView,
    MyInformationRetrieveUpdateDestroyView,
    UserListCreateView,
    UserRetrieveUpdateDestroyView,
)

urlpatterns = [
    # Google Authentication Endpoint
    path("auth/google/", GoogleAuthView.as_view(), name="google-auth"),
    #
    # my information endpoints
    # path(
    #     "my-information/",
    #     MyInformationListCreateView.as_view(),
    #     name="myinformation-list-create",
    # ),
    path(
        # "my-information/me/",
        "my-information/",
        MyInformationRetrieveUpdateDestroyView.as_view(),
        name="myinformation-detail",
    ),
    #
    # User endpoints
    path(
        "user/",
        UserListCreateView.as_view(),
        name="user-list-create",
    ),
    path(
        "user/<uuid:id>/",
        UserRetrieveUpdateDestroyView.as_view(
            lookup_field="id",
        ),
        name="user-retrieve-update-destroy",
    ),
    #
    # first responder endpoints
    path(
        "first-responders/",
        FirstResponderListCreateView.as_view(),
        name="firstresponder-list-create",
    ),
    path(
        "first-responders/<uuid:pk>/",
        FirstResponderRetrieveUpdateDestroyView.as_view(),
        name="firstresponder-retrieve-update-destroy",
    ),
]
