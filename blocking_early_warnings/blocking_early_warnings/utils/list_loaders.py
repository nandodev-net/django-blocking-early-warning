"""
    Functions to load lists into the database
"""

# External imports
import requests as req
from requests.exceptions import HTTPError

# Local imports
from blocking_early_warnings.models import ASN, UrlList, Url

# Python imports
from typing import List


def sync_urllists_db():
    """
    This function updates url lists to match those in the lists
    """
    urls = {}
    lists = UrlList.objects.all()

    for list in lists:
        # get urls for this source
        url_list = get_list_from_storage(list.source, list.storage_type)
        url_list = get_urls_from_list_content(url_list, list.parse_strategy)

        # store url in map
        for url in url_list:

            # if not in the dict, init it to an empty list
            if (source_list := urls.get(url)) is None:
                source_list = urls[url] = []

            source_list.append(list)

    # Delete non-relevant urls
    non_relevant_urls = Url.objects.exclude(url__in=urls.keys())
    non_relevant_urls.delete()

    # update urls
    for (url, lists) in urls.items():
        url_object, _ = Url.objects.get_or_create(url=url, defaults={"url": url})
        url_object.lists.clear()

        for list in lists:
            url_object.lists.add(list)

        url_object.save()


def get_list_from_storage(location: str, storage: str) -> str:
    """
    Get a list content located in "location" with storage type "storage"
    Location may vary depending on storage type. For example, in a local_storage list,
    location may be a file path, whilst in web_storage location may be an url

    Parameters:
        + location : str = str specifying a mean to locate the list
        + storage  : str = storage type, possible options specified by UrlList.StorageType enum
    Return:
        string with list content
    """

    if storage == UrlList.StorageType.WEB_REQUEST:
        return get_list_from_web_request(location)
    if storage == UrlList.StorageType.LOCAL_STORAGE:
        return get_list_from_local_storage(location)
    else:
        raise ValueError(f"Unrecognized storage type: {storage}")


def get_list_from_local_storage(path: str) -> str:
    """
    Get list content from a local file
    Parameters:
        + path : str = path to file containing the list
    Return:
        string contained by the file
    """
    with open(path, "r") as list:
        return list.read()


def get_list_from_web_request(url: str) -> str:
    """
    Get list from a get request to a given url
    Parameters:
        + url : str = valid url to a list containing the list
    Return:
        string returned by the url
    """

    # Try to get data from url
    try:
        response = req.get(url)
    except:
        raise HTTPError(f"Could not retrieve urls from source: {url}")

    # If could not retrieve data, raise an error
    if response.status_code != 200:
        raise HTTPError(f"Could not retrieve urls from source: {url}")

    return response.text


def get_urls_from_list_content(list_content: str, strategy: str) -> List[str]:
    """
    Get urls from a string with a list of urls.
    Parameters:
        + source_url : str = url list formated as specified by "strategy"
        + strategy : str = strategy to parse text. Can be one of:
                - citizen_lab_csv
                - url_list_txt
            Note that these variants are the same as in UrlList.ParseStrategy
    Return:
        URL list from the the given formated list
    """

    # Parse urls according to the expected strategy
    if strategy == UrlList.ParseStrategy.CITIZEN_LAB_CSV:
        return parse_urls_from_csv_str(list_content)
    elif strategy == UrlList.ParseStrategy.URL_LIST_TXT:
        return parse_urls_from_txt_str(list_content)


def parse_urls_from_csv_str(csv: str) -> List[str]:
    """
    Given a csv formated string with an url list as the following:
        https://raw.githubusercontent.com/citizenlab/test-lists/master/lists/ve.csv
    Return the url list
    Parameters:
        + csv : str =  a string formated as a csv
    Return:
        A list of urls
    """

    # Get csv lines
    lines = csv.splitlines(keepends=False)

    # get first col from every line from 1 to n
    first_cols = map(lambda r: r.split(",")[0].strip(), lines[1:])

    return list(first_cols)


def parse_urls_from_txt_str(txt: str) -> List[str]:
    """
    Given string with a list of urls separated by new line,
    return a list of urls
    Parameters:
        + txt : str = str with a list of urls separated by new line
    Return:
        A list of urls as described by the string
    """
    lines = txt.splitlines(keepends=False)
    lines = map(lambda l: l.strip(), lines)

    return list(lines)
