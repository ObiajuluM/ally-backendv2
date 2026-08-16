from django.urls import include, path
from ally.views import (
    GeminidView,
    GoogleAuthView,
    MyInformationRetrieveUpdateDestroyView,
    RegisterFCMTokenView,
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
    # # User endpoints
    # path(
    #     "users/",
    #     UserListCreateView.as_view(),
    #     name="user-list-create",
    # ),
    path(
        "user/",
        UserRetrieveUpdateDestroyView.as_view(),
        name="user-retrieve-update-destroy",
    ),
    # FCM
    # "register-fcm"
    path("fcm/", RegisterFCMTokenView.as_view(), name="register-fcm-token"),
    # Gemini
    path("geminid/", GeminidView.as_view(), name="geminid"),
    #
    path("first-responder/", include("firstresponder.urls")),
    path("ally-alert/", include("allyalert.urls")),
    path("live-location/", include("livelocation.urls")),
    path("chat/", include("chat.urls")),
]
