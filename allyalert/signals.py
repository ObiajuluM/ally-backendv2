from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from celery import chain
from .models import AllyAlert
from .tasks import create_alert_deliveries, send_alert_push_notifications


# Chain the two tasks so notifications only fire AFTER all delivery
# rows are committed. .si() (immutable signature) means the return
# value of create_alert_deliveries is not passed as an argument to
# send_alert_push_notifications — each task receives only its own args.
# this method wil be fired if any AllyAlert instance is created and saved to the database
@receiver(post_save, sender=AllyAlert)
def create_ally_alert_delivery(sender, instance, created, **kwargs):
    print(f"Post-save signal triggered for AllyAlert {instance.pk}, created={created}")
    # Strictly limit execution to new object creation
    if created:
        # Pass the execution logic safely to the transaction commit hook
        transaction.on_commit(
            lambda: chain(
                create_alert_deliveries.si(str(instance.pk)),
                send_alert_push_notifications.si(str(instance.pk)),
            ).apply_async()
        )
