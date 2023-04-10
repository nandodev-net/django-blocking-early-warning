"""
    Functions to request data from ooni and save it to database if needed
"""
# External imports
from django.db.models import Max
from pytz import utc
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
from blocking_early_warnings.utils.misc import get_hour_from_str, get_hour

# Python imports
from datetime import datetime, timedelta
from urllib.parse import urlencode
from typing import Any, Dict, Optional, Tuple, List, Dict


class DBMetricsClient:
    """Manage database metrics, you can sync them with this object"""

    def __init__(
        self,
        number_of_hours: int = NUMBER_OF_HOURS,
        date_format: str = DATE_FORMAT,
        country_code: str = COUNTRY_CODE,
        ooni_endpoint: str = OONI_ENDPOINT,
    ):

        self._number_of_hours = number_of_hours
        self._date_format = date_format
        self._country_code = country_code
        self._ooni_endpoint = ooni_endpoint

    def sync_db_metrics(self, number_of_hours: Optional[int] = None):
        """
        Sync metrics with current ooni data
        """

        number_of_hours = number_of_hours or self._number_of_hours

        # Compute required time interval from now until NUMBER_OF_HOURS before
        now = get_hour(datetime.now(tz=utc))
        yesterday = now - timedelta(hours=number_of_hours)

        # Get ooni data
        data = self.get_raw_data_from_ooni(since=yesterday, until=now, page_size=5000)
        # Process data
        metrics = map(
            lambda k: (k[0], self.compute_metrics(k[1], since=get_hour(yesterday))),
            data.items(),
        )

        url_map = {url.url: url for url in Url.objects.all()}
        asn_map = {asn.code: asn for asn in ASN.objects.all()}

        for m in metrics:
            # deconstruct m in url, asn, and data
            ((url, asn), data) = m

            url_obj, asn_obj = url_map[url], asn_map[asn]
            # Use max hour to filter metrics that should not be added as they already have a previous version
            max_hour = (
                Metric.objects.all()
                .filter(asn=asn_obj, url=url_obj)
                .aggregate(Max("hour"))["hour__max"]
            )
            max_hour = max_hour or datetime(1970, 1, 1, tzinfo=utc)

            for d in data.items():

                (hour, data_metrics) = d

                # Dont create empty metrics as it will blow up the database quite fast
                if data_metrics["count"] == 0:
                    continue

                # Don't add metrics that are more recent than the most recent one
                if hour <= (max_hour):
                    continue

                Metric.objects.update_or_create(
                    hour=hour,
                    anomaly_count=data_metrics["anomaly_count"],
                    measurement_count=data_metrics["count"],
                    url=url_obj,
                    asn=asn_obj,
                )

    def compute_metrics(
        self,
        measurements: List[Dict[str, Any]],
        since: datetime,
        number_of_hours: Optional[int] = None,
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

        number_of_hours = number_of_hours or self._number_of_hours

        # utility function to get hour from time
        start_time = lambda m: m["measurement_start_time"]

        # Classify by hour
        classified = {
            since + timedelta(hours=i): {"count": 0, "anomaly_count": 0}
            for i in range(number_of_hours)
        }

        for measurement in measurements:
            hour = get_hour_from_str(start_time(measurement))

            metrics = classified[hour]

            metrics["anomaly_count"] += measurement["anomaly"]
            metrics["count"] += 1

        return classified

    def get_raw_data_from_ooni(
        self,
        since: datetime,
        until: datetime,
        country_code: Optional[str] = None,
        page_size: int = 1000,
        ooni_endpoint: Optional[str] = None,
        date_format: Optional[str] = None,
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

        # Setup default arguments
        country_code = country_code or self._country_code
        ooni_endpoint = ooni_endpoint or self._ooni_endpoint
        date_format = date_format or self._date_format

        # Set up arguments
        since_str = datetime.strftime(since, date_format)
        until_str = datetime.strftime(until, date_format)

        args = {
            "since": since_str,
            "until": until_str,
            "probe_cc": country_code,
            "limit": page_size,
        }

        next_url = f"{ooni_endpoint}?{urlencode(args)}"

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
        classifier_dict = self._get_classifier_dict_url_asns()

        for item in acc:
            asn = item["probe_asn"]
            url = item["input"]

            if (curr_list := classifier_dict.get((url, asn))) is not None:
                curr_list.append(item)

        return classifier_dict

    def _get_classifier_dict_url_asns(self) -> Dict[Tuple[str, str], List[Any]]:
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
