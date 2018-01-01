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
    _UPLOADED_BYTES = 'UploadedBytes'
    _DOWNLOADED_BYTES = 'DownloadedBytes'

    @property
    def total(self) -> int:
        return self.up + self.down

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
            self._UPLOADED_BYTES: self.up,
            self._DOWNLOADED_BYTES: self.down
        }

    def __init__(self, dt: datetime.datetime, up: int, down: int):
        """
        Initialise a new usage sample.

        :param dt: The beginning of the hour this usage is for. Any units
                   smaller than hour are ignored.
        :param up: The amount of data uploaded during the hour in bytes.
        :param down: The amount of data downloaded during the hour in bytes.
        """
        self.dt = dt.replace(minute=0, second=0, microsecond=0) \
                    .astimezone(pytz.utc)
        self.up = up
        self.down = down

    @staticmethod
    def parse_line(line: str) -> 'HourUsage':
        """
        Parse a single line outputted by the legacy script running on lon-1.

        :param line: A line of the form "<ISO8601 datetime>,<uploaded bytes>,
                     <downloaded bytes>", e.g. "2017-08-30T08:00:00+00:00,
                     17620000,14650000"
        :return: A usage sample representing the line.
        """
        dt, up, down = line.split(',', 2)
        return HourUsage(dateutil.parser.parse(dt)
                                 .astimezone(pytz.utc),
                         int(up),
                         int(down))

    @classmethod
    def parse_item(cls, item: Dict[str, Union[str, decimal.Decimal]]) \
            -> 'HourUsage':
        """
        Parse the JSON representation of a sample stored in DynamoDB.

        :param item: The item JSON to parse.
        :return: A usage sample representing the item.
        """
        return HourUsage(dateutil.parser
                                 .parse(item[cls._DATE_HOUR])
                                 .astimezone(pytz.utc),
                         int(item[cls._UPLOADED_BYTES]),
                         int(item[cls._DOWNLOADED_BYTES]))

    def __eq__(self, other: 'HourUsage') -> bool:
        return other.dt == self.dt \
               and other.up == self.up \
               and other.down == self.down

    def __str__(self) -> str:
        return 'HourUsage({0}, Uploaded: {1}, Downloaded: {2})'.format(
            self.dt.isoformat(),
            util.format_bytes(self.up),
            util.format_bytes(self.down))

    def __repr__(self) -> str:
        return '<HourUsage({0},{1},{2})>'.format(repr(self.dt), repr(self.up),
                                                 repr(self.down))
