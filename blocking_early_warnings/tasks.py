from celery import shared_task
import blocking_early_warnings.utils.ooni_requests as ooni_requests
import blocking_early_warnings.utils.list_loaders as list_loaders
import blocking_early_warnings.utils.anomaly_monitor as anomaly_monitor


@shared_task(time_limit=3600, name="blocking_early_warnings.synch_metrics")
def synch_db_metrics():
    """
    Asynch process to get raw data from ooni.
    Will update database so metrics object are up to date
    with current hour and online ooni data
    """
    client = ooni_requests.DBMetricsClient()
    client.sync_db_metrics()


@shared_task(time_limit=3600, name="blocking_early_warnings.synch_urls")
def synch_urls():
    """
    Asynch process to get updated urls from known sources
    """
    loader = list_loaders.ListLoader()
    loader.sync_urllists_db()


@shared_task(time_limit=3600, name="blocking_early_warnings.monitor_anomalies")
def monitor_anomalies():
    """Asynch process to check for anomalies in the database and notify as specified"""
    monitor = anomaly_monitor.AnomalyMonitor()
    monitor.analize_db_metrics(should_act=True)
