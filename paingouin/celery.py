import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paingouin.settings")

app = Celery("paingouin")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "cleanup-transactions-every-10-minutes": {
        "task": "commande.tasks.refresh_transactions",
        "schedule": 600.0,  # 600 seconds = 10 minutes
    },
}
