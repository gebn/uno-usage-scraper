# -*- coding: utf-8 -*-
import unittest
import datetime
import pytz

from hour_usage import HourUsage


class TestHourUsage(unittest.TestCase):

    _NOW = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    _GRANULAR_DATE = datetime.datetime(2018, 10, 27, 22, 25, 22, 342, pytz.utc)
    _USAGE = HourUsage(_GRANULAR_DATE, 3487529, 934785)
    _ITEM = {
        'DateHour': '2018-10-27T22Z',
        'DownloadedBytes': 3487529,
        'UploadedBytes': 934785
    }

    def test_units_more_granular_than_hour_stripped(self):
        coarse = datetime.datetime(2018, 10, 27, 22, tzinfo=pytz.utc)
        usage = HourUsage(self._GRANULAR_DATE, 0, 0)
        self.assertEqual(usage.dt, coarse)

    def test_total(self):
        self.assertEqual(HourUsage(self._NOW, 45, 34).total, 79)

    def test_item(self):
        self.assertDictEqual(self._USAGE.item, self._ITEM)

    def test_parse_line_insufficient(self):
        with self.assertRaises(ValueError):
            HourUsage.parse_line('foo')

    def test_parse_line(self):
        usage = HourUsage.parse_line(
            '2017-08-30T08:00:00+00:00,14650000,17620000')
        self.assertEqual(usage.dt,
                         datetime.datetime(2017, 8, 30, 8, tzinfo=pytz.utc))
        self.assertEqual(usage.down, 14650000)
        self.assertEqual(usage.up, 17620000)

    def test_parse_item_malformed_dt(self):
        with self.assertRaises(ValueError):
            HourUsage.parse_item({**self._ITEM, 'DateHour': 'invalid'})

    def test_parse_item_mistyped_dt(self):
        with self.assertRaises(ValueError):
            HourUsage.parse_item({**self._ITEM, 'DateHour': 13})

    def test_parse_item_mistyped_down(self):
        with self.assertRaises(ValueError):
            HourUsage.parse_item({**self._ITEM, 'DownloadedBytes': 'foo'})

    def test_parse_item_mistyped_up(self):
        with self.assertRaises(ValueError):
            HourUsage.parse_item({**self._ITEM, 'UploadedBytes': 'bar'})

    def test_parse_item_missing_dt(self):
        copy = self._ITEM.copy()
        del copy['DateHour']
        with self.assertRaises(ValueError):
            HourUsage.parse_item(copy)

    def test_parse_item_missing_up(self):
        copy = self._ITEM.copy()
        del copy['DownloadedBytes']
        with self.assertRaises(ValueError):
            HourUsage.parse_item(copy)

    def test_parse_item_missing_down(self):
        copy = self._ITEM.copy()
        del copy['UploadedBytes']
        with self.assertRaises(ValueError):
            HourUsage.parse_item(copy)

    def test_parse_item(self):
        self.assertEqual(HourUsage.parse_item(self._ITEM), self._USAGE)

    def test_eq(self):
        self.assertEqual(self._USAGE, self._USAGE)

    def test_eq_false(self):
        self.assertNotEqual(self._USAGE, HourUsage(self._GRANULAR_DATE, 0, 1))
