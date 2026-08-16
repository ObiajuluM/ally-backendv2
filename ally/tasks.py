# --------------------------------------------------------------------------
# SEND WELCOME EMAIL
# --------------------------------------------------------------------------
# tasks.py

from celery import shared_task
from django.contrib.auth import get_user_model

from ally.mail.welcome import send_welcome_email

User = get_user_model()


@shared_task
def send_welcome_email_task(user_id):
    user = User.objects.get(id=user_id)
    send_welcome_email(user)
