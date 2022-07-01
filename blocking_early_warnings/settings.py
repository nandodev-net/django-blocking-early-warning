"""
    File with a few constants to use throughout the app
"""
import os

# How many hours do we store
NUMBER_OF_HOURS = 24

# ooni endpoit to request data from
OONI_ENDPOINT = "https://api.ooni.io/api/v1/measurements"

# Date format
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Country code of interesting country
COUNTRY_CODE = "VE"

# Tolerance for the anomaly trigering algorithm
TOLERANCE = 0.1

# Mail to notify when an alert happens
MAIL_TO_NOTIFY = os.environ.get("BLOCKING_EARLY_WARNING_NOTIFY_MAIL")

SENDER_MAIL = os.environ.get("BLOCKING_EARLY_WARNING_SENDER_MAIL")

SENDER_MAIL_PSWD = os.environ.get("BLOCKING_EARLY_WARNING_SENDER_MAIL_PSWD")
