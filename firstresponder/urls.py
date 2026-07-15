from django.urls import path

from firstresponder.views import FirstResponderListCreateView

urlpatterns = [
    path(
        "",
        FirstResponderListCreateView.as_view(),
        name="firstresponder-list-create",
    ),
    #
    # path(
    #     "first-responders/<uuid:pk>/",
    #     FirstResponderRetrieveUpdateDestroyView.as_view(),
    #     name="firstresponder-retrieve-update-destroy",
    # ),
    #
]
