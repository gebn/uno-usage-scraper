# -*- coding: utf-8 -*-
from typing import Iterable, List, Tuple, Type
import logging
import re
import datetime
import pytz
import requests

from hour_usage import HourUsage

_TZ_LONDON = pytz.timezone('Europe/London')
_UTC_NOW = datetime.datetime.now(pytz.utc)
_LONDON_NOW = _TZ_LONDON.normalize(_UTC_NOW)

logger = logging.getLogger(__name__)


class UnoError(Exception):
    """
    Represents a generic error encountered while interacting with Uno.
    """

    def __init__(self, message: str):
        """
        Initialise a new UnoError.

        :param message: A description of the nature of the error.
        """
        self.message = message

    def __str__(self) -> str:
        return f'{self.__class__.__name__}({self.message})'


class ParseError(UnoError):
    """
    Raised when there is an issue extracting information from the portal's
    HTML. This is effectively only possible when the markup has changed.
    """

    def __init__(self, message: str, html: str):
        """
        Initialise a new parse error.

        :param message: A description of the nature of the error.
        :param html: The original page HTML.
        """
        super().__init__(message)
        self.html = html

    def __str__(self) -> str:
        return f'{self.__class__.__name__}({self.message}, {self.html})'


class DailyUsageExtractor:
    """
    Retrieves usage for each of the last 24 hours for a user.
    """

    _DAILY_USAGE_FMT = 'https://my.uno.net.uk/uno/unousagedaily.php?' \
                       'id={product_id}'
    _ENTRY_REGEX = r'"(\d+)\\n((?:a|p)m)",\W*(\d+(?:.\d+)?)'

    def __init__(self, version: str, url: str):
        """
        Initialise a new daily usage extractor.

        :param version: The version of this software to report to Uno.
        :param url: A URL explaining the function of this software.
        """
        self._version = version
        self._url = url

    @staticmethod
    def _parse_entry(match: Tuple[str, str, str]) \
            -> Tuple[datetime.datetime, int]:
        """
        Turns a raw HTML match into a time and a number of bytes.

        :param match: The array element match, e.g. `('5', 'pm', '2779.14')`.
                      The first element is the (12 hour clock) hour of day,
                      the second is "am" or "pm", and the third is usage during
                      that hour in megabytes.
        :return: A tuple of the hour's aware datetime and number of bytes
        """
        hour = int(match[0])
        is_afternoon = match[1] == 'pm'

        if hour == 12 or is_afternoon:
            hour = (hour + 12) % 24

        if hour == 0 and is_afternoon:
            hour = 12

        # turn hour into datetime
        time = datetime.datetime(year=_LONDON_NOW.year,
                                 month=_LONDON_NOW.month,
                                 day=_LONDON_NOW.day,
                                 hour=hour,
                                 tzinfo=_TZ_LONDON)

        if hour >= _LONDON_NOW.hour:
            # was yesterday
            time -= datetime.timedelta(days=1)

        bytes_ = int(float(match[2]) * 1e6)
        return time, bytes_

    @classmethod
    def _extract_variable_entries(cls: Type['DailyUsageExtractor'], html: str,
                                  name: str) \
            -> List[Tuple[str, str, str]]:
        """
        Finds and does a basic pattern match against the contents of a variable
        containing daily usage data. On the portal, there are two array
        variables, one for download and one for upload, each containing hourly
        usage in megabytes.

        :param html: The page HTML.
        :param name: The name of the variable to find and parse.
        :return: A list of parsed contents for each element in the variable.
                 Guaranteed not to be empty.
        :raises ParseError: If no data points could be extracted.
        """
        value_match = re.search(r'var {0} = (.+);'.format(name), html)
        if value_match is None:
            raise ParseError(f'Could not find variable {name}', html)
        value_points = re.findall(cls._ENTRY_REGEX, value_match.group(1))
        if not value_points:
            raise ParseError(f'Could not extract any usage samples from '
                             f'variable {name}', html)
        return value_points

    @classmethod
    def _extract_data_points(cls, html: str) -> Iterable[HourUsage]:
        """
        Combined parsed data points into a sequence of HourlyUsage objects.

        :param html: The complete page HTML.
        :return: An ordered sequence of 24 HourlyUsage objects.
        :raises ParseError: If the dates in the download and upload arrays do
                            not correspond.
        """
        download_entries = cls._extract_variable_entries(html, 'data')
        upload_entries = cls._extract_variable_entries(html, 'data2')
        for down, up in zip(download_entries, upload_entries):
            d_time, d_bytes = cls._parse_entry(down)
            u_time, u_bytes = cls._parse_entry(up)
            if d_time != u_time:
                raise ParseError('Download/upload array data points '
                                 'do not match up', html)
            yield HourUsage(d_time.astimezone(pytz.utc), u_bytes, d_bytes)

    def extract(self, product_id: int, whmcs_user: str) -> Iterable[HourUsage]:
        """
        Retrieve the last 24 hours' usage data for a user.

        :param product_id: The unique identifier of the product to measure,
                           e.g. 1799.
        :param whmcs_user: A valid WHMCSUser cookie for the user.
        :return: 24 HourUsage objects in ascending date order, representing
                 usage during the period.
        :raises UnoError: If any error occurred during extraction; check the
                          message for details.
        """
        response = requests.get(
            self._DAILY_USAGE_FMT.format(product_id=product_id),
            headers={
                'User-Agent': f'uno-usage-scraper/{self._version} '
                              f'({self._url})'
            },
            cookies={
                'WHMCSUser': whmcs_user
            })
        logger.debug(f'{response}: {response.text}')
        if not response.ok:
            raise UnoError(f'Portal returned HTTP {response.status_code}')
        return self._extract_data_points(response.text)
