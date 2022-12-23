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


class ListLoader:
    """Manage list loading into the database"""

    def sync_urllists_db(self):
        """
        This function updates url lists to match those in the lists
        """
        urls = {}
        lists = UrlList.objects.all()

        for list in lists:
            # get urls for this source
            url_list = self.get_urls_from_list(list)

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

    def get_urls_from_list(self, list: UrlList) -> List[str]:
        """Get urls from a list, parsing it according to the specified location, storage type and parse strategy

        Args:
            location (str): Where to locate the list. Ignored when storage_type == db
            storage_type (StorageType): How this list is stored. Should request it from the web? Is it a local file? Can be retrieved from db?
            parse_strategy (ParseStrategy): How to parse this list, should be one of the known ways. Ignored when storage_type == db
            list_name (str): Name of this list, specially important for db-based lists

        Returns:
            List[str]: resulting list of urls
        """

        if list.storage_type == UrlList.StorageType.LOCAL_STORAGE:
            url_list_str = self.get_list_from_local_storage(list.source)
        elif list.storage_type == UrlList.StorageType.WEB_REQUEST:
            url_list_str = self.get_list_from_web_request(list.source)
        elif list.storage_type == UrlList.StorageType.DB:
            return self.get_list_from_db(list)
        else:
            raise ValueError(f"Unrecognized storage type: {list.storage_type}")

        return self.parse_urls_from_list_content(url_list_str, list.parse_strategy)

    def get_list_from_local_storage(self, path: str) -> str:
        """
        Get list content from a local file
        Parameters:
            + path : str = path to file containing the list
        Return:
            string contained by the file
        """
        with open(path, "r") as list:
            return list.read()

    def get_list_from_web_request(self, url: str) -> str:
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

    def get_list_from_db(self, url_list: UrlList) -> List[str]:
        """Get urls related to the specified list of urls

        Args:
            list (UrlList): List object specifying the urls to retrieve

        Returns:
            List[str]: List of urls as strings
        """

        return [url.url for url in url_list.url_set.all()]  # type: ignore

    def parse_urls_from_list_content(
        self, list_content: str, strategy: str
    ) -> List[str]:
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

        raise ValueError(
            f"'{strategy}' is not a valid strategy, choices are: {UrlList.ParseStrategy.values}"
        )


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
