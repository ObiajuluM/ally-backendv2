# utils/email.py

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_welcome_email(user):
    subject = "Welcome to Ally 🎉"

    context = {
        "user": user,
    }

    html = render_to_string(
        "mail/welcome.html",
        context,
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body="Welcome to Ally!",
        to=[user.email],
    )

    email.attach_alternative(html, "text/html")
    email.send()
