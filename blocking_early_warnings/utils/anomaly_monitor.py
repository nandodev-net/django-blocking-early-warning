"""
    This module implements the anomaly monitoring logic, like sending emails on relevant alerts
"""


# Python imports
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from itertools import product
import dataclasses
import ssl, smtplib
from pytz import utc

# Local imports
from blocking_early_warnings.models import ASN, Metric, Url
from blocking_early_warnings.settings import (
    TOLERANCE,
    MAIL_TO_NOTIFY,
    SENDER_MAIL,
    SENDER_MAIL_PSWD,
)


class IssueType(Enum):
    """Possible variants of issue
    ok: Everything ok, there's no issue
    spike: There was a sudden spike of anomalies for a given pair (url,asn)
    high_anomaly_rate: There's too many measurements with anomalies
    """

    OK = "ok"
    SPIKE = "spike"
    HIGH_ANOMALY_RATE = "high_anomaly_rate"

    @property
    def description(self) -> str:
        """return a description specifying what kind of problem represents this issue type

        Returns:
            str: Description telling what kind of problem this issue is
        """
        desc_map = {
            IssueType.OK: "Everything ok, no actual issue was found",
            IssueType.SPIKE: "There is a metric with high a amount of anomalies",
            IssueType.HIGH_ANOMALY_RATE: "There is a high amount of anomalies in multiple metrics",
        }

        assert (
            self in desc_map
        ), f"'{self}' does not have a description. Maybe you added a new issue type variant but forgot to add its description?"

        return desc_map[self]

    @property
    def human_readable(self) -> str:
        """Return a human readable name for this type of anomaly

        Returns:
            str: human readable name
        """

        human_map = {
            IssueType.OK: "ok",
            IssueType.SPIKE: "Spike in amount of anomalies",
            IssueType.HIGH_ANOMALY_RATE: "High anomaly rate",
        }

        assert (
            self in human_map
        ), f"'{self}' does not have an human readable name. Maybe you added a new issue type variant but forgot to add its human readable name?"
        return human_map[self]


@dataclasses.dataclass
class IssueDescription:
    """Information describing an issue"""

    asn: ASN
    metrics: List[Metric]
    url: Url
    issue_type: IssueType


class AnomalyMonitor:
    """Compute anomalies for each pair (asn, url), and update them in the database."""

    def __init__(
        self,
        sender_mail: Optional[str] = SENDER_MAIL,
        sender_mail_pswd: Optional[str] = SENDER_MAIL_PSWD,
        mail_to_notify: Optional[str] = MAIL_TO_NOTIFY,
    ) -> None:

        self._sender_mail = sender_mail
        self._sender_mail_pswd = sender_mail_pswd
        self._mail_to_notify = mail_to_notify

    def analize_db_metrics(
        self,
        start_time: Optional[datetime] = None,
        tolerance: float = TOLERANCE,
        should_act: bool = False,
    ) -> List[IssueDescription]:
        """Analize currently stored metrics in db, return the list of found issues

        Args:
            start_time (Optional[datetime], optional): The lastest time to look for metrics. Defaults to 24 hours ago.
            tolerance (float, optional): A tolerance value telling how much variation  in the anomaly rate to accept. Defaults to TOLERANCE.
            should_act (bool, optional) : If should do something if issues are found. Defaults to False. 
        Raises:
            NotImplementedError: _description_

        Returns:
            List[IssueDescription]: _description_
        """

        # Defaults to 24 hours ago
        end_time = datetime.now(tz=utc) - timedelta(hours=1)
        start_time = start_time or end_time - timedelta(hours=24)

        # Get metrics to analyze
        metrics = self._get_metrics_for_url_and_asn(
            start_time=start_time, end_time=end_time
        )

        results = []
        for ((asn, url), metric_list) in metrics.items():
            issue = self.compute_anomaly(
                asn=asn, url=url, metrics=metric_list, spike_tolerance=tolerance
            )
            # Return only if important
            if issue.issue_type != IssueType.OK:
                results.append(issue)

            # Act only if requested to
            if should_act:
                self.act(issue)

        return results

    def _get_metrics_for_url_and_asn(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[Tuple[ASN, Url], List[Metric]]:
        """Built a mapping from (ASN, URL) to a list of metrics starting from 'start_time'

        Parameters:
            start_time (Optional[datetime]) : latest date to look metrics from.
            start_time (Optional[datetime]) : earliest date to look metrics from.

        Returns:
            Dict[Tuple[ASN, Url], List[Metric]]: Return a Dict mapping from a tuple of ASN and a list of metrics. Every metric holds:
            start_time <= metric.hour <= end_time
        """
        asns = ASN.objects.all()
        urls = Url.objects.all()

        result = {}
        for (url, asn) in product(urls, asns):
            result[(asn, url)] = Metric.objects.all().filter(
                url=url, asn=asn, hour__gte=start_time, hour__lte=end_time
            )

        return result

    def compute_anomaly(
        self,
        metrics: List[Metric],
        spike_tolerance: float,
        asn: ASN,
        url: Url,
        should_sort: bool = False,
        anomaly_ratio_avg_tolerance: float = 0.2,
    ) -> IssueDescription:
        """Compute an issue type for the given set of metrics.

        An anomaly is an unexpected spike on the anomaly count. This is computed by iterating over the list of metrics
        and computing the mean and variance of the anomaly ratio at each hoyr

        Args:
            metrics (List[Metric]): A list of metrics to check for anomalies. It is expected that all of them
            will have the same asn and url, but this is not actually checked for performance reasons

            should_sort (bool) : Sort the provided list of metrics to ascending order by hour if true.  Defaults to false.

            anomaly_ratio_avg_tolerance (float) : If the average of anomaly ratio per metric in the given list is > anomaly_ratio_avg_tolerance,
            raise a high_anomaly_rate issue

        Returns:
            IssueType: The type of issue detected on the given set of metrics
        """

        # Quit if nothing to do
        ok_issue = IssueDescription(
            asn=asn, metrics=[], url=url, issue_type=IssueType.OK
        )
        if not metrics:
            return ok_issue

        if should_sort:
            metrics.sort(key=lambda x: x.hour)

        anomaly_ratio = [m.anomaly_count / m.measurement_count for m in metrics]

        # Compute averange and variance
        avg = sum(anomaly_ratio) / len(anomaly_ratio)
        var = (
            sum((r - avg) ** 2 for r in anomaly_ratio) / (len(anomaly_ratio) - 1)
            if len(anomaly_ratio) > 1
            else 0
        )

        # Check for high anomaly rate
        if avg > anomaly_ratio_avg_tolerance:
            return IssueDescription(
                asn=asn,
                metrics=metrics,
                url=url,
                issue_type=IssueType.HIGH_ANOMALY_RATE,
            )

        # Check for spikes
        spikes = [
            m
            for (m, r) in zip(metrics, anomaly_ratio)
            if r > (avg + var + spike_tolerance)
        ]

        if spikes:
            return IssueDescription(
                asn=asn, metrics=spikes, url=url, issue_type=IssueType.SPIKE
            )

        return ok_issue

    def act(self, issue: IssueDescription):
        """Take the necessary actions for the given issue, depending on its properties

        Args:
            issue (IssueDescription): An issue, namely an anomaly and its corresponding data
        """

        if IssueType.OK == issue.issue_type:
            return  # Do nothing about it if everything ok

        if issue.url.alert_level != Url.AlertCategory.ALERT:
            return  # Do nothing about it if alert level won't require it

        # If important enough to mail it, then compose email and send it
        title, mail_content = self._compose_mail(issue)
        self._send_mail(title, mail_content)

    def _compose_mail(self, issue: IssueDescription) -> Tuple[str, str]:
        """Compose an email describing the provided issue. Return a string with the message to send

        Args:
            issue (IssueDescription): Issue to expose

        Returns:
            Tuple[str, str]: title, and a string with a message explaining the specified issue in an human readable manner
        """
        assert issue.metrics

        sample_issue = issue.metrics[0]

        issue_description = issue.issue_type.description
        issue_name = issue.issue_type.human_readable

        email_title = f"ALERT: [{issue_name}] On {issue.url.url} for {issue.asn.name or issue.asn.code}"
        email_content = f"{issue_description}, on url '{sample_issue.url.url}' for asn '{sample_issue.asn.name}' ('{sample_issue.asn.code}')\nAlarming metric(s): \n"

        email_content = email_content + "\n".join(
            [
                f"\t- Hour: {m.hour}, measurement count: {m.measurement_count}, anomaly count: {m.anomaly_count}"
                for m in issue.metrics
            ]
        )

        avg_anomaly_ratio = sum(
            m.anomaly_count / m.measurement_count for m in issue.metrics
        ) / len(issue.metrics)
        if issue.issue_type == IssueType.HIGH_ANOMALY_RATE:
            email_content += f"\nAvg anomaly ratio: {avg_anomaly_ratio}"
        elif issue.issue_type == IssueType.SPIKE:
            email_content += f"\nAnomaly ratio is: {avg_anomaly_ratio}"

        return email_title, email_content

    def _send_mail(self, title: str, message: str):

        sender = self._sender_mail
        reciever = self._mail_to_notify
        psswd = self._sender_mail_pswd

        print(sender, psswd)

        # Don't try anything if parameters are not properly configured
        if not psswd or not reciever or not sender:
            raise ValueError(
                f"Can't send email because there's a missing configuration parameter"
            )

        msg = f"Subject: {title}\n\n{message}"

        # set up email server config
        port = 465
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
            server.login(sender, psswd)
            server.sendmail(sender, reciever, msg)
