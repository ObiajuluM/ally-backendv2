from django.urls import path

from livelocation.views import UserIsStreamingView

urlpatterns = [
    path(
        "is-streaming/",
        UserIsStreamingView.as_view(),
        name="user-is-streaming-view",
    ),
]
