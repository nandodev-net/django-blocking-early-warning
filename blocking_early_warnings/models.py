# Django imports
from typing_extensions import Self
from django.db import models
from django.db.models.signals import post_save

# Local imports
from blocking_early_warnings.settings import NUMBER_OF_HOURS

# Python imports
from typing import Type, Optional, Iterable


class UrlList(models.Model):
    """
    Represents a source to get a list of URLs from.
    Note that since the system should be able to parse from
    different sources, they may not have the same format,
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
        DB = "db"  # Stored in the local database and managed with admin

    # List name, for example: "citizen lab"
    name = models.TextField(max_length=100, unique=True, null=False)

    # Url to request list itself. Null when Storage Type is DB
    source = models.TextField(
        verbose_name="Content source path (leave blank if storage_type is db)",
        null=True,
        blank=True,
    )

    # How this list should be parsed
    parse_strategy = models.TextField(
        choices=ParseStrategy.choices, default=ParseStrategy.CITIZEN_LAB_CSV, null=True
    )

    # How this list is stored, local or online
    storage_type = models.TextField(
        choices=StorageType.choices, default=StorageType.WEB_REQUEST, null=False
    )

    def save(self, *args, **kwargs) -> None:

        # Consistency check: when storage type is "db" is not necessary to specify
        # a source
        if self.storage_type == UrlList.StorageType.DB and self.source:
            raise ValueError(
                f"'source' field should be set to blank or None when 'storage_type' is set to 'db'. Source = {self.source}"
            )
        # Consistency check: Unless storage type == db, source and parse strategy should be != none so you can find all urls
        elif self.storage_type != UrlList.StorageType.DB and (
            not self.source or self.parse_strategy == None
        ):
            raise ValueError(
                f"'source' and 'parse_strategy' should both be set to some value when 'storage_type' != 'db'. parse_strategy = {self.parse_strategy}, source = {self.source}"
            )

        return super().save(*args, **kwargs)

    def __repr__(self) -> str:
        return f"[{self.name}] strategy: {self.parse_strategy}, storage: {self.storage_type}"

    def __str__(self) -> str:
        return self.__repr__()


class Url(models.Model):
    """
    An url to be processed by our pipeline
    """

    class AlertCategory(models.TextChoices):
        """Specify the kind of alert required for an URL. The highest level implies"""

        # Just ignore an anomaly for this event
        MUTED = "muted"

        # Alert using email
        ALERT = "alert"

    # Alert level: which set of actions are taken when an anomaly is detected on this url
    alert_level = models.TextField(
        verbose_name="Alert Level",
        choices=AlertCategory.choices,
        default=AlertCategory.MUTED,
    )

    url = models.TextField(max_length=100, null=False, unique=True)
    lists = models.ManyToManyField(to=UrlList)

    def __repr__(self) -> str:
        return f"Url(url = {self.url}, alert_level = {self.alert_level})"

    def __str__(self) -> str:
        return self.__repr__()

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

    def __str__(self) -> str:
        return self.__repr__()


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


class EarlyWarningSettings(models.Model):
    """Represents the moduel configuration editable via django admin"""

    number_of_days_back = models.IntegerField(
        verbose_name="Number of days back to check", default=30
    )

    # Override save method to make this a singleton
    def save(self, *args, **kwargs) -> None:
        self.pk = 1
        return super().save(*args, **kwargs)

    # Do nothing, the only instance should be never deleted
    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls) -> Self:
        """
        Get the settings object
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
