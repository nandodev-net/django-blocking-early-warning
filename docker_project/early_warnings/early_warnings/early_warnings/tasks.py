"""
    This files contains definitions for async process
"""
# Python imports
import datetime
import celery
import pytz

# Third party imports
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
