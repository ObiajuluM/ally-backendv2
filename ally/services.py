from firebase_admin import messaging
from ally.models import UserDevice


def fcm_send_push_notification(user, title, body, extra_data=None):
    """
    Sends a push notification to all active devices of a given user.
    """
    print(f"Sending push notification to user: {user.email}")
    devices = UserDevice.objects.filter(user=user)
    if not devices.exists():
        return False, "No registered devices for this user"

    tokens = [device.fcm_token for device in devices]

    # Construct FCM Multicast Message
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=extra_data
        or {},  # Optional payload dictionary (e.g. {'screen': 'sos_details', 'id': '123'})
        tokens=tokens,
        # iOS specific payload for badge / sound configuration
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(aps=messaging.Aps(sound="default", badge=1))
        ),
        # Android specific configuration
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                sound="default",
                channel_id="ally_fcm_channel_id",
            ),
        ),
    )

    response = messaging.send_each_for_multicast(message)

    # Clean up stale/invalid tokens
    if response.failure_count > 0:
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                # Token might be expired or unregistered
                failed_token = tokens[idx]
                UserDevice.objects.filter(fcm_token=failed_token).delete()

    print(
        f"Successfully sent {response.success_count} messages, failed {response.failure_count} messages."
    )

    return True, f"Successfully sent {response.success_count} messages"
