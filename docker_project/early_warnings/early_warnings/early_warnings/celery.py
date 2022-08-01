"""
    Configurations file for celery
"""
import os

# Third party imports
from celery import Celery

# Set settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "early_warnings.settings")

# Create celery app
app = Celery("early_warnings")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
