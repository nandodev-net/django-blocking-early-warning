from celery import shared_task
import blocking_early_warnings.utils.ooni_requests as ooni_requests


@shared_task(time_limit=3600, name="blocking_early_warnings.synch_metrics")
def synch_db_metrics():
    """
    Asynch process to get raw data from ooni.
    Will update database so metrics object are up to date
    with current hour and online ooni data
    """
    ooni_requests.sync_db_metrics()
