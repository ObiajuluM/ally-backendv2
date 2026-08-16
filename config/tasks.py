from celery import shared_task
from django.utils import timezone

# --------------------------------------------------------------------------
# PERIODIC TASKS  (scheduled via celery-beat)
# --------------------------------------------------------------------------


@shared_task
def cleanup_celery_results():
    """
    Deletes django-celery-results TaskResult rows older than 7 days.

    The TaskResult table grows unboundedly without this — it stores the
    return value, arguments, and traceback of every task that ran.

    Run once daily via celery-beat.
    """

    from django_celery_results.models import TaskResult

    # Define a 30-day lookback window from the current time to select all task results older than 30 days. These will be deleted to prevent the TaskResult table from growing unboundedly.
    cutoff = timezone.now() - timezone.timedelta(days=30)
    # Delete records older than the cutoff date in a single database query.
    # 'deleted' captures the count of rows removed; '_' ignores the per-model breakdown dict.
    deleted, _ = TaskResult.objects.filter(date_done__lt=cutoff).delete()

    # Return a summary string showing the total number of purged logs
    return f"{deleted} old task result(s) deleted"
