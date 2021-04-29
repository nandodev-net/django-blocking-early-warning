# Django imports
from django.db import models
from django.db.models.signals import post_save

# Local imports
from blocking_early_warnings.settings import NUMBER_OF_HOURS

# Python imports
from typing import Type


class UrlList(models.Model):
    """
    Represents a source to get a list of URLs from.
    Note that since the system should be able to parse from
    different sources, they may have not the same format,
    so we provide a few default formats:
        CITIZEN_LAB_CSV = a csv file from citizen lab as https://raw.githubusercontent.com/citizenlab/test-lists/master/lists/ve.csv
        URL_LIST_TXT    = a txt with a different url in each line
    """

    # Possible strategies to parse this url
    class ParseStrategy(models.TextChoices):
        CITIZEN_LAB_CSV = "citizen_lab_csv"
        URL_LIST_TXT = "url_list_txt"

    class StorageType(models.TextChoices):
        LOCAL_STORAGE = "local_storage"  # stored in local machine
        WEB_REQUEST = "web_request"  # requested by get request

    # List name, for example: "citizen lab"
    name = models.TextField(max_length=100, unique=True, null=False)

    # Url to request list itself
    source = models.TextField(verbose_name="Content source path")

    # How this list should be parsed
    parse_strategy = models.TextField(
        choices=ParseStrategy.choices, default=ParseStrategy.CITIZEN_LAB_CSV
    )

    # How this list is stored, local or online
    storage_type = models.TextField(
        choices=StorageType.choices, default=StorageType.WEB_REQUEST
    )

    def __repr__(self) -> str:
        return f"[{self.name}] stratey: {self.parse_strategy}, storage: {self.storage_type}"


class Url(models.Model):
    """
    An url to be processed by our pipeline
    """

    url = models.TextField(max_length=100, null=False, unique=True)
    lists = models.ManyToManyField(to=UrlList)

    def __repr__(self) -> str:
        return self.url

    @staticmethod
    def post_save(
        sender, instance, created, raw, using, update_fields, *args, **kwargs
    ):
        """
        Create a valid set of metrics for this new instance
        """
        # if not a new instance, do nothing
        if not created:
            return

        asns = ASN.objects.all()

        # create a new metric for each asn
        for asn in asns:
            for _ in range(NUMBER_OF_HOURS):
                metric = Metric(asn=asn, url=instance)
                metric.save()


post_save.connect(Url.post_save, sender=Url)


class ASN(models.Model):
    """
    ASN used to classify urls
    """

    # Asn name, for example: cantv
    name = models.TextField(max_length=100, null=True)

    # ASN code, for example: AS8048
    code = models.TextField(unique=True, max_length=100, null=False)

    @staticmethod
    def post_save(
        sender, instance, created, raw, using, update_fields, *args, **kwargs
    ):
        """
        Create a valid set of metrics for every URL with this asn
        """
        # if not a new instance, do nothing
        if not created:
            return

        urls = Url.objects.all()
        for url in urls:
            for _ in range(NUMBER_OF_HOURS):
                metric = Metric(asn=instance, url=url)
                metric.save()

    def __repr__(self) -> str:
        return f"{self.code} - {self.name}"


post_save.connect(ASN.post_save, sender=ASN)


class Metric(models.Model):
    """
    A metric for an URL. Every URL has 24 metrics per ASN, one per hour
    for such asn
    """

    # Hour for this metric
    hour = models.DateTimeField(null=True, default=None)

    # How many anomalies in this hour
    anomaly_count = models.IntegerField(null=True, default=None)

    # How many measurements in this hour
    measurement_count = models.IntegerField(null=True, default=None)

    # ASN for this measurement
    asn = models.ForeignKey(to=ASN, null=False, on_delete=models.CASCADE)

    # URL related to this metric
    url = models.ForeignKey(to=Url, null=False, on_delete=models.CASCADE)

    def __repr__(self) -> str:
        return f"Metric(hour={self.hour}, anomaly_count={self.anomaly_count}, measurement_count={self.measurement_count}, asn={self.asn}, url={self.url})"
