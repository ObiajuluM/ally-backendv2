from celery import shared_task
from django.utils import timezone


@shared_task
def cleanup_orphaned_live_sessions():
    """
    Closes any LiveLocationSession that was never properly ended.

    A session is considered orphaned when:
      - ended_at is still null (publisher never disconnected cleanly), AND
      - all of its participants have a left_at timestamp (everyone is gone).

    This can happen if the server restarts mid-session, a container is killed,
    or a network drop prevents the disconnect signal from firing.

    Run once daily via celery-beat.
    """
    from livelocation.models import LiveLocationSession

    now = timezone.now()

    # Find sessions that are still "open" (no ended_at).
    open_sessions = LiveLocationSession.objects.filter(ended_at__isnull=True)

    closed = 0
    for session in open_sessions:
        participants = session.participants.all()

        # A session with no participants at all is also orphaned — the
        # publisher connected but nothing ever happened.
        all_left = (
            participants.exists()
            and not participants.filter(left_at__isnull=True).exists()
        )
        no_participants = not participants.exists()

        if all_left or no_participants:
            session.ended_at = now
            session.save(update_fields=["ended_at"])
            closed += 1

    return f"{closed} orphaned session(s) closed"
