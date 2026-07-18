from celery import shared_task
from django.utils import timezone

# --------------------------------------------------------------------------
# TRIGGERED TASKS
# These are fired manually (e.g. from a view) when something happens.
# --------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def create_alert_deliveries(self, alert_id: str):
    """
    Finds every user whose saved location falls within the alert's radius
    and creates one AlertDelivery row per user.

    - Uses bulk_create with ignore_conflicts=True so the task is idempotent:
      re-running it (e.g. after a retry) will never produce duplicate rows.
    - Only users with a non-null location can be matched geographically.
    - The creator is excluded — they don't need to receive their own alert.

    Chained with: send_alert_push_notifications
    """
    print(f"Running create_alert_deliveries for alert {alert_id}...")
    from allyalert.models import AllyAlert, AlertDelivery
    from ally.models import User
    from django.contrib.gis.measure import D

    try:
        alert = AllyAlert.objects.get(pk=alert_id)
    except AllyAlert.DoesNotExist:
        # Alert was deleted before the task ran — nothing to do.
        return

    # Skip delivery if the alert is already expired or removed.
    if alert.status != AllyAlert.Status.ACTIVE:
        return

    # Skip if no target location is set yet (shouldn't happen in normal flow,
    # but guards against bad data during development).
    if not alert.target_location or not alert.radius_km:
        return

    # Find all users whose last known location is within the alert radius.
    # geography=True on the field means distance is calculated in metres on
    # the earth's surface, so D(km=...) gives accurate real-world distances.
    nearby_users = (
        User.objects.filter(
            location__dwithin=(alert.target_location, D(km=float(alert.radius_km))),
        )
        .exclude(pk=alert.creator_id)  # creator already knows about their own alert
        .exclude(location__isnull=True)  # can't match users with no location
        .values_list("id", flat=True)
    )

    deliveries = [
        AlertDelivery(alert=alert, user_id=user_id) for user_id in nearby_users
    ]

    if not deliveries:
        return

    # ignore_conflicts=True makes this safe to retry — duplicate rows are silently skipped.
    AlertDelivery.objects.bulk_create(deliveries, ignore_conflicts=True)
    # Delivery rows are now written. The chain in the view will automatically
    # trigger send_alert_push_notifications next — no manual .delay() needed here.


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_alert_push_notifications(self, alert_id: str):
    """
    Sends a push notification / WebSocket event to every user that has an
    AlertDelivery row for this alert.

    Currently a stub — wire in your push provider (FCM, APNs, etc.) here.
    The delivery rows are already written by create_alert_deliveries before
    this task runs.
    """
    from allyalert.models import AllyAlert, AlertDelivery

    try:
        alert = AllyAlert.objects.select_related("creator").get(pk=alert_id)
    except AllyAlert.DoesNotExist:
        return

    # Fetch every user ID that should receive this notification.
    recipient_ids = AlertDelivery.objects.filter(alert=alert).values_list(
        "user_id", flat=True
    )

    # TODO: integrate your push provider here.
    # Example payload to send to each device token:
    # {
    #     "title": alert.title,
    #     "body": alert.description[:100],
    #     "data": {"alert_id": str(alert.id)},
    # }
    for user_id in recipient_ids:
        pass  # replace with: fcm_send(token=get_token(user_id), ...)


# --------------------------------------------------------------------------
# PERIODIC TASKS  (scheduled via celery-beat)
# --------------------------------------------------------------------------


@shared_task
def expire_stale_alerts():
    print("Running expire_stale_alerts...")
    """
    Marks every ACTIVE alert whose expires_at is in the past as EXPIRED.

    Run every 5 minutes via celery-beat.

    This keeps the public list view accurate — the list filters by
    status=ACTIVE, so without this task stale alerts would show forever.
    """
    from allyalert.models import AllyAlert

    updated = AllyAlert.objects.filter(
        status=AllyAlert.Status.ACTIVE,
        expires_at__lt=timezone.now(),
    ).update(
        status=AllyAlert.Status.EXPIRED,
        updated_at=timezone.now(),
    )

    print(
        f"000000000000000000000  {updated} alert(s) marked as EXPIRED -- can remove later, i left for debug 0000000000000000000000"
    )

    return f"{updated} alert(s) marked as EXPIRED"
