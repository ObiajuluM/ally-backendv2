# celery job stuff

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()  # Finds tasks.py in every INSTALLED_APP
app.autodiscover_tasks(
    ["config"]
)  # explicitly include config, for the periodic cleanup task defined in "config/tasks.py"
