from django.urls import path

from .views import ChatView, SendMessageView

urlpatterns = [
    path("", ChatView.as_view()),
    path("message/", SendMessageView.as_view()),
]
