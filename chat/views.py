# views.py

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.actions import appropriate_response_from_text
from config import settings

from .models import Chat, Message
from .serializers import ChatSerializer, MessageSerializer


class ChatView(APIView):
    def get_permissions(self):
        if not settings.DEBUG:
            self.permission_classes = [
                IsAuthenticated,
            ]
        return super().get_permissions()

    def get(self, request):
        chat, _ = Chat.objects.get_or_create(user=request.user)

        serializer = ChatSerializer(chat)

        return Response(serializer.data)


class SendMessageView(APIView):
    def get_permissions(self):
        if not settings.DEBUG:
            self.permission_classes = [
                IsAuthenticated,
            ]
        return super().get_permissions()

    def post(self, request):
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chat, _ = Chat.objects.get_or_create(user=request.user)

        message = Message.objects.create(
            chat=chat,
            role=Message.Role.USER,
            content=serializer.validated_data["content"],
        )
        # get AI reponse and save it as a system message
        reply_message = Message.objects.create(
            chat=chat,
            role=Message.Role.SYSTEM,
            content=appropriate_response_from_text(
                serializer.validated_data["content"]
            ),
        )

        return Response(
            {
                "id": message.id,
                "content": message.content,
                "role": message.role,
                "created_at": message.created_at,
                "reply": reply_message,
            },
            status=status.HTTP_200_OK,
        )
