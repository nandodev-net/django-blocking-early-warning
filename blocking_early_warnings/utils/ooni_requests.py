"""
    Functions to request data from ooni
"""
# External imports
from requests.exceptions import HTTPError
from blocking_early_warnings.utils.list_loaders import parse_urls_from_csv_str
import requests as req

# Local imports
from blocking_early_warnings.models   import Metric, ASN, Url
from blocking_early_warnings.settings import OONI_ENDPOINT, DATE_FORMAT, COUNTRY_CODE

# Python imports
from datetime import datetime
from urllib.parse import urlencode

def get_raw_data_from_ooni(since : datetime, until : datetime) -> dict:
    """
        Get requests from ooni 
    """
    # Set up arguments
    since = datetime.strftime(since, DATE_FORMAT)
    until = datetime.strftime(until, DATE_FORMAT)

    args = {
        "since" : since,
        "until" : until,
        "probe_cc" : COUNTRY_CODE,
        "limit" : 10000
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

        metadata = data['metadata']
        acc.extend(data['results'])

        # Where to get next page
        next_url = metadata['next_url']

    # Classify retrieved data based on url,asn
    classifier_dict = _get_classifier_dict__url_asns()

    for item in acc:
        asn = item['probe_asn']
        url = item['input']
        print(f"({url}, {asn})")
        if (curr_list := classifier_dict.get((url, asn))):
            curr_list.append(item)

    return classifier_dict

def _get_classifier_dict__url_asns() -> dict:
    """
        Helper function to get a dict using for classifyiend data inputs according
        to its asn and input
    """
    urls = Url.objects.all()
    asns = ASN.objects.all()
    cl_dict = {}

    for url in urls.iterator():
        for asn in asns:
            cl_dict[(url.url, asn.code)] = []

    return cl_dict