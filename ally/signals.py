# signals.py

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Address, MyInformation, User
from .tasks import send_welcome_email_task


# When a User is deleted, also delete their linked MyInformation.
# This is necessary because the FK lives on User, so Django's built-in
# CASCADE only protects the reverse direction (MyInformation → User).
@receiver(post_delete, sender=User)
def delete_my_information_on_user_delete(sender, instance, **kwargs):
    if instance.my_information_id:
        MyInformation.objects.filter(pk=instance.my_information_id).delete()


# When a MyInformation row is deleted (e.g. triggered by the signal above),
# also delete the linked Address row.
@receiver(post_delete, sender=MyInformation)
def delete_address_on_my_information_delete(sender, instance, **kwargs):
    if instance.address_id:
        Address.objects.filter(pk=instance.address_id).delete()


# send welcome email when a new user is created
@receiver(post_save, sender=User)
def welcome_email(sender, instance, created, **kwargs):
    if created:
        send_welcome_email_task.delay(instance.id)
