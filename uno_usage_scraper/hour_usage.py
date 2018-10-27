# -*- coding: utf-8 -*-
from typing import Dict, Union
import decimal
import datetime
import pytz
import dateutil.parser

import util


class HourUsage:
    """
    Represents the usage on a line during a one-hour period.
    """

    _DATE_HOUR = 'DateHour'
    _DOWNLOADED_BYTES = 'DownloadedBytes'
    _UPLOADED_BYTES = 'UploadedBytes'

    @property
    def total(self) -> int:
        return self.down + self.up

    @property
    def item(self) -> Dict[str, Union[str, int]]:
        """
        Retrieve the item representation of this sample for use when inserting
        it into DynamoDB. This should be the inverse of parse_item() such that
        `HourUsage.parse_item(sample.item) == sample`.

        :return: The DynamoDB representation of this sample.
        """
        return {
            self._DATE_HOUR: f'{self.dt:%Y-%m-%dT%HZ}',
            self._DOWNLOADED_BYTES: self.down,
            self._UPLOADED_BYTES: self.up
        }

    def __init__(self, dt: datetime.datetime, down: int, up: int):
        """
        Initialise a new usage sample.

        :param dt: The beginning of the hour this usage is for. Any units
                   smaller than hour are ignored. Should be timezone-aware.
        :param down: The amount of data downloaded during the hour in bytes.
        :param up: The amount of data uploaded during the hour in bytes.
        """
        self.dt = dt.replace(minute=0, second=0, microsecond=0)
        self.down = down
        self.up = up

    @staticmethod
    def parse_line(line: str) -> 'HourUsage':
        """
        Parse a single line outputted by the legacy script running on lon-1.

        :param line: A line of the form "<ISO8601 datetime>,<downloaded bytes>,
                     <uploaded bytes>", e.g.
                     "2017-08-30T08:00:00+00:00,14650000,17620000".
        :return: A usage sample representing the line.
        """
        dt, down, up = line.split(',', 2)
        return HourUsage(dateutil.parser.parse(dt)
                                 .astimezone(pytz.utc),
                         int(down),
                         int(up))

    @classmethod
    def parse_item(cls, item: Dict[str, Union[str, decimal.Decimal]]) \
            -> 'HourUsage':
        """
        Parse the JSON representation of a sample stored in DynamoDB.

        :param item: The item JSON to parse.
        :return: A usage sample representing the item.
        :raises ValueError: If the item is missing a field or malformed.
        """
        try:
            return HourUsage(dateutil.parser
                                     .parse(item[cls._DATE_HOUR])
                                     .astimezone(pytz.utc),
                             int(item[cls._DOWNLOADED_BYTES]),
                             int(item[cls._UPLOADED_BYTES]))
        except KeyError as e:
            raise ValueError('Missing key') from e
        except TypeError:
            raise ValueError('The DateHour must be a string')

    def __eq__(self, other: 'HourUsage') -> bool:
        return other.dt == self.dt \
               and other.down == self.down \
               and other.up == self.up

    def __str__(self) -> str:
        return 'HourUsage({0}, Downloaded: {1}, Uploaded: {2})'.format(
            self.dt.isoformat(),
            util.format_bytes(self.down),
            util.format_bytes(self.up))

    def __repr__(self) -> str:
        return '<HourUsage({0},{1},{2})>'.format(
            repr(self.dt), repr(self.down), repr(self.up))
