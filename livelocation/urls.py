from django.urls import path

from livelocation.views import SendSMSView, UserIsStreamingView

urlpatterns = [
    path(
        "send-sms/",
        SendSMSView.as_view(),
        name="send-sms-view",
    ),
    path(
        "is-streaming/",
        UserIsStreamingView.as_view(),
        name="user-is-streaming-view",
    ),
]
