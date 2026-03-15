from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from config import settings
from .models import FirstResponder, MyInformation, User
from .serializers import (
    FirstResponderSerializer,
    MyInformationSerializer,
    UserSerializer,
)
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests

# from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken


class GoogleAuthView(APIView):
    def post(self, request):
        try:
            token = request.data.get("id_token")
            if not token:
                return Response(
                    {"error": "ID token not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify token with Google
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )

            email = idinfo["email"]
            name = idinfo.get("name", "")

            # Get or create user, the created bool indicates if a new user was created or an existing one was found
            user, created = User.objects.get_or_create(
                email=email,
                # only used when a new user is created.If the user already exists, defaults does not update anything.
                defaults={
                    "email": email,
                    "username": name if name else "",
                },
            )

            # Only a brand-new user gets an initial MyInformation record here.
            # Returning users keep whatever profile is already linked to them.
            if created:
                user.my_information = MyInformation.objects.create(name=name)
                user.save(update_fields=["my_information"])

            # Issue JWT token
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MyInformationListCreateView(ListCreateAPIView):
    queryset = MyInformation.objects.select_related("address").all()
    serializer_class = MyInformationSerializer


class MyInformationRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    queryset = MyInformation.objects.select_related("address")
    serializer_class = MyInformationSerializer


class UserListCreateView(ListCreateAPIView):
    queryset = User.objects.select_related("my_information")
    # queryset = MyInformation.objects.prefetch_related("myInformation")
    serializer_class = UserSerializer


class UserRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.select_related("my_information")
    # queryset = MyInformation.objects.prefetch_related("myInformation")
    serializer_class = UserSerializer


class FirstResponderListCreateView(ListCreateAPIView):
    # use select_related() for instead of prefetch_related() to optimize queries
    # since we are dealing with a single related object (address and socials)
    queryset = FirstResponder.objects.select_related(
        "address",
    )
    serializer_class = FirstResponderSerializer


class FirstResponderRetrieveUpdateDestroyView(RetrieveUpdateDestroyAPIView):
    queryset = FirstResponder.objects.select_related(
        "address",
    )
    serializer_class = FirstResponderSerializer
