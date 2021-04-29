"""
    Functions to request data from ooni
"""
# External imports
from django.db.models import signals
from django.db.models.query_utils import InvalidQuery
from requests.exceptions import HTTPError
import requests as req

# Local imports
from blocking_early_warnings.models import Metric, ASN, Url
from blocking_early_warnings.settings import (
    OONI_ENDPOINT,
    DATE_FORMAT,
    COUNTRY_CODE,
    NUMBER_OF_HOURS,
)
from blocking_early_warnings.utils.misc import Accumulator, get_hour_str, get_hour

# Python imports
from datetime import datetime, timedelta
from urllib.parse import urlencode
from typing import Any, Dict, Tuple, List, Dict


def sync_db_metrics():
    """
    Sync metrics with current ooni data
    """

    # Compute required time interval from now until NUMBER_OF_HOURS before
    now = get_hour(datetime.now())
    yesterday = now - timedelta(hours=NUMBER_OF_HOURS)

    # Get ooni data
    data = get_raw_data_from_ooni(since=yesterday, until=now, page_size=5000)
    # Process data
    metrics = map(
        lambda k: (k[0], compute_metrics(k[1], since=get_hour(yesterday))), data.items()
    )

    # Get all metrics
    all_metrics = Metric.objects.select_related("url", "asn").all()

    # callback function to efficiently update metrics
    def update_metrics(metrics):
        Metric.objects.bulk_update(
            metrics, ["hour", "anomaly_count", "measurement_count"]
        )

    # create an accumulator object to bulk update metrics
    updater = Accumulator(update_metrics)

    for m in metrics:
        # deconstruct m in url, asn, and data
        ((url, asn), data) = m

        # retrieve metrics
        curr_metrics = all_metrics.filter(asn__code=asn, url__url=url)

        # check for consistency
        if (amnt := curr_metrics.count()) != NUMBER_OF_HOURS:
            raise InvalidQuery(
                f"Inconsistent database: There should be {NUMBER_OF_HOURS} metrics instance for url {url} and asn {asn}, but {amnt} were found"
            )

        # order data by date
        data = sorted(data.items(), key=lambda d: d[0])

        i = 0
        for metric in curr_metrics:
            (hour, data_metrics) = data[i]
            metric.hour = hour
            metric.anomaly_count = data_metrics["anomaly_count"]
            metric.measurement_count = data_metrics["count"]

            updater.add(metric)

            i += 1

        print(data)

    print(list(metrics))


def compute_metrics(
    measurements: List[Dict[str, Any]], since: datetime
) -> Dict[datetime, Dict[str, int]]:
    """
    Return a dict with the following data for the provided list:
        + Anomaly count
        + Mesurement count
    Separated by hour, for example:

    {
        datetime(day=2,year=2020,month=2, hour=22) : {
            anomaly_count : 42
            measurement_count : 69
        }

        datetime(day=2,year=2020,month=2, hour=23)  : {
            anomaly_count : 73
            measurement_count : 420
        }
    }
    Parameters:
        + measurements : [dict] = List of measurement metadata as it comes from ooni
        + since : datetime = Initial hour for this measurement list
    Return:
        a dict with specified format
    """

    # utility function to get hour from time

    # shortcut function
    start_time = lambda m: m["measurement_start_time"]

    # Classify by hour
    classified = {
        since + timedelta(hours=i): {"count": 0, "anomaly_count": 0}
        for i in range(NUMBER_OF_HOURS)
    }

    for measurement in measurements:
        hour = get_hour_str(start_time(measurement))
        metrics = classified[hour]

        metrics["anomaly_count"] += measurement["anomaly"]
        metrics["count"] += 1

    return classified


def get_raw_data_from_ooni(
    since: datetime,
    until: datetime,
    country_code: str = COUNTRY_CODE,
    page_size: int = 1000,
) -> Dict[Tuple[str, str], List[Any]]:
    """
    Get data from ooni from "since" until "until" in a dict with the following format:
        {
            (url, asn) : [Measurement]
        }
        Where Measurement is a measurement data as it comes from ooni
    Parameters:
        + since : datetime = Start time for measurements
        + since : datetime = Start time for measurements
        + country_code  : str = Country code that all measurements should have
        + page_size     : int = how many measurements request for each page
    Return:
        dict with the specified data format
    """

    assert page_size > 0, "page size should be greater than 0"

    # Set up arguments
    since = datetime.strftime(since, DATE_FORMAT)
    until = datetime.strftime(until, DATE_FORMAT)

    args = {
        "since": since,
        "until": until,
        "probe_cc": country_code,
        "limit": page_size,
    }

    next_url = f"{OONI_ENDPOINT}?{urlencode(args)}"

    acc = []

    while next_url:
        print(f"next url is: {next_url}")
        # Perform get request
        request = req.get(next_url)

        # check if everything went ok
        if request.status_code != 200:
            raise HTTPError("Could not retrieve ooni data")

        # Get data in json format
        data = request.json()

        metadata = data["metadata"]
        acc.extend(data["results"])

        # Where to get next page
        next_url = metadata["next_url"]

    # Classify retrieved data based on url,asn
    classifier_dict = _get_classifier_dict_url_asns()

    for item in acc:
        asn = item["probe_asn"]
        url = item["input"]
        if (curr_list := classifier_dict.get((url, asn))) is not None:
            curr_list.append(item)

    return classifier_dict


def _get_classifier_dict_url_asns() -> Dict[Tuple[str, str], List[Any]]:
    """
    Helper function to get a dict using for classifyiend data inputs according
    to its asn and input
    """
    # Get all urls, asns
    urls = Url.objects.all()
    asns = ASN.objects.all()

    # init output
    cl_dict = {}

    for url in urls.iterator():
        for asn in asns:
            cl_dict[(url.url, asn.code)] = []

    return cl_dict
