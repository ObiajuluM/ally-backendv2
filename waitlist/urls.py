from django.urls import path
from .views import WaitlistView

urlpatterns = [
    path("join/", WaitlistView.as_view(), name="waitlist-join"),
]
