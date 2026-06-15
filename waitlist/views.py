from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from waitlist.serializers import WaitlistSerializer
from .models import WaitlistEntry


class WaitlistView(APIView):
    def post(self, request):
        serializer = WaitlistSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        _, created = WaitlistEntry.objects.get_or_create(email=email)
        if created:
            return Response(
                {"message": "You have been added to the waitlist."},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": "This email is already on the waitlist."},
            status=status.HTTP_200_OK,
        )
