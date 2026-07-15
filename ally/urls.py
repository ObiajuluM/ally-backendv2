from django.urls import path
from ally.views import (
    GeminidView,
    GoogleAuthView,
    MyInformationRetrieveUpdateDestroyView,
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
    # # User endpoints
    # path(
    #     "user/",
    #     UserListCreateView.as_view(),
    #     name="user-list-create",
    # ),
    path(
        "user/",
        UserRetrieveUpdateDestroyView.as_view(),
        name="user-retrieve-update-destroy",
    ),
    # Gemini
    path("geminid/", GeminidView.as_view(), name="geminid"),
]
