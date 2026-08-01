# celery job stuff

import os
from celery import Celery

from config import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
# This single line handles everything dynamically
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# app.autodiscover_tasks(
#     ["config",]
# )  # explicitly include config, for the periodic cleanup task defined in "config/tasks.py"
# app.autodiscover_tasks()  # Finds tasks.py in every INSTALLED_APP
