"""
We implement the histogram backend data generation in this file. 

TODO We have to decide whether to save anomalies as a database table, or compute them
on the fly using the anomaly monitor class each time you want to check for anomalies. 
I think this depends on the performance penalty and should be measured in the future with 
production-level data
"""

# Python imports
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass
from pytz import utc

# Local imports
from blocking_early_warnings.models import Metric

@dataclass
class HistogramBlockData:
    """Data generated for a single histogram block
    """

    # Block value
    hour : datetime

    # Block data
    total_count : int
    anomaly_count : int 




class HistogramGenerator:
    """Generate Histograms data for the histogram page.
    For now is just an utility class to compute a query, but might get bigger in the future. 
    """

    @staticmethod
    def histogram(url : Optional[str] = None, asn : Optional[str] = None, start_date : Optional[datetime] = None, end_date : Optional[datetime] = None) -> List[HistogramBlockData]:
        """Generate the content of a histogram. Returns a list of metrics, which represent the blocks in
        the histogram.

        Args:
            url (Optional[str]): String naming the corresponding url to measure. If not provided, don't filter by ur;. Defaults to None.
            asn (Optional[str]): String naming the asn (by code) that all metrics should share. Don't filter if not provided. Defaults to None.
            start_date (Optional[datetime]): Date of the earliest metric. Defaults to 24 before end_date if not provided. Defaults to None.
            end_date (Optional[datetime]): Date of the latest metric. Defaults to now if not provided. Defaults to None.

        Returns:
            List[Metric]: List of metrics that represent blocks for a histogram, where the block value is the hour.
        """
        qs = Metric.objects.all()

        # Filter by url and asn if provided
        if url:
            qs = qs.filter(url__url = url)
        if asn:
            qs = qs.filter(asn__code = asn)

        # Setup date
        end_date = end_date or datetime.now(tz=utc)
        start_date = start_date or end_date - timedelta(hours=24)

        assert start_date < end_date, \
                f"Provided invalid date interval to generate histograms, start_date ({start_date}) should be before end_date ({end_date})"
        
        # filter by hour
        qs = qs.filter(hour__gte = start_date, hour__lte = end_date)

        # Collect blocks
        blocks = {}

        for metric in qs:
            metric_instance : Metric = metric

            # Check if already added
            block = blocks.get(metric_instance.hour) 
            if not block: # If not, add a default with all zeroes
                block = blocks[metric_instance.hour] = HistogramBlockData(
                    hour=metric_instance.hour, 
                    total_count=0, 
                    anomaly_count=0
                )

            # Add the new metric's data
            block.total_count += metric_instance.measurement_count
            block.anomaly_count += metric_instance.anomaly_count


        result = list(blocks.values())
        result.sort(key=lambda b: b.hour)
        return result

