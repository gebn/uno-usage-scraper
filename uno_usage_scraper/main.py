# -*- coding: utf-8 -*-
from typing import Iterable, Collection, Dict
import logging
import os
import json
import time
import datetime
import pytz
import dateutil.parser
import boto3

import util
from hour_usage import HourUsage
from uno import DailyUsageExtractor


_VERSION = '1.0.0'
_EXECUTION_TOLERANCE = datetime.timedelta(minutes=5)

_UTC_NOW = datetime.datetime.now(pytz.utc)
_UNO_USER_ID = int(os.environ['UNO_USER_ID'])
_UNO_COOKIE = util.kms_decrypt_str(os.environ['UNO_COOKIE'])
_UNO_COOKIE_EXPIRES = dateutil.parser.parse(os.environ['UNO_COOKIE_EXPIRES'])
_UNO_COOKIE_WARNINGS = bool(os.getenv('UNO_COOKIE_WARNINGS', True))
_UNO_COOKIE_WARNING_THRESHOLD = datetime.timedelta(weeks=2)
_NOTIFICATION_TOPIC_ARN = os.environ['NOTIFICATION_TOPIC_ARN']
_NOTIFICATION_TOPIC_REGION = _NOTIFICATION_TOPIC_ARN.split(':')[3]
_USAGE_PUSHOVER_APP_TOKEN = util.kms_decrypt_str(
    os.environ['USAGE_PUSHOVER_APP_TOKEN'])
_SEND_USAGE = bool(os.getenv('SEND_USAGE', True))
_DYNAMO_REGION = os.environ['AWS_REGION']
_DYNAMO_TABLE = os.environ['DYNAMO_TABLE']

_SNS = boto3.client('sns', region_name=_NOTIFICATION_TOPIC_REGION)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _timely_execution_check(event: Dict, context) -> None:
    """
    Sends a warning if this function executed unacceptably early or late.

    :param event: The CloudWatch event trigger that resulted in this function
                  being executed.
    :param context: The context object of the current execution.
    """
    if 'time' not in event:
        # this event was triggered via some other means, e.g. manually, so
        # there is nothing to validate
        logger.debug('Not validating execution time as the function was '
                     'triggered by something other than a CloudWatch event')
        return
    event_time = dateutil.parser.parse(event['time'])
    if event_time < _UTC_NOW - _EXECUTION_TOLERANCE or \
            event_time > _UTC_NOW + _EXECUTION_TOLERANCE:
        response = _SNS.publish(
            TopicArn=_NOTIFICATION_TOPIC_ARN,
            Message=f'Lambda function {context.function_name} executed too '
                    'early or too late:\n'
                    f'Request: {context.aws_request_id}\n'
                    f"Event: {event['id']}\n"
                    f'Expected: {event_time}\n'
                    f'Actual: {_UTC_NOW}')
        logger.info(f"Published time warning: {response['MessageId']}")


def _cookie_expiry_check() -> None:
    """
    Ensures the cookie we will use to interact with Uno does not expire within
    the next _UNO_COOKIE_WARNING_THRESHOLD. If it does, send a warning alert.
    """
    validity_remaining = _UNO_COOKIE_EXPIRES - _UTC_NOW
    if validity_remaining < _UNO_COOKIE_WARNING_THRESHOLD:
        response = _SNS.publish(
            TopicArn=_NOTIFICATION_TOPIC_ARN,
            Message=f'Uno cookie will expire in {validity_remaining}')
        logger.info(f"Published cookie warning: {response['MessageId']}")


def _usage_summary(samples: Iterable[HourUsage]) -> None:
    """
    Creates and sends a usage summary from the current period.

    :param samples: The samples to compute the summary from.
    """
    samples = [(point.up, point.down) for point in samples]
    up, down = [sum(metric) for metric in zip(*samples)]
    message = {
        'app': _USAGE_PUSHOVER_APP_TOKEN,
        'body': f'{util.format_bytes(up)} up, {util.format_bytes(down)} down'
    }
    response = _SNS.publish(
        TopicArn=_NOTIFICATION_TOPIC_ARN,
        Message=json.dumps(message, ensure_ascii=False))
    logger.info(f"Published usage summary: {response['MessageId']}")


def _insert_samples(samples: Collection[HourUsage], table) -> None:
    """
    Adds a collection of samples to a DynamoDB table.

    :param samples: The samples to insert.
    :param table: The table to insert the samples into.
    """
    with table.batch_writer() as batch:
        start = time.monotonic()
        for sample in samples:
            logger.debug(f'Putting {sample}')
            batch.put_item(Item=sample.item)
    end = time.monotonic()
    seconds = end - start
    logger.info('Inserted %d samples in %.3fs (%.3f/s)',
                len(samples), seconds, len(samples) / seconds)


def main() -> None:
    """
    Executes the main bulk of this function. Here for manual execution outside
    of Lambda.

    :raises UnoError: If any error occurs during execution.
    """
    utc_now_hour = _UTC_NOW.replace(minute=0, second=0, microsecond=0)
    lower = utc_now_hour - datetime.timedelta(hours=23)
    upper = utc_now_hour - datetime.timedelta(hours=11)

    extractor = DailyUsageExtractor(_VERSION)
    samples = extractor.extract(_UNO_USER_ID, _UNO_COOKIE)
    subset = [point for point in samples if lower <= point.dt < upper]

    if _UNO_COOKIE_WARNINGS:
        _cookie_expiry_check()

    if _SEND_USAGE:
        _usage_summary(subset)

    resource = boto3.resource('dynamodb', region_name=_DYNAMO_REGION)
    table = resource.Table(_DYNAMO_TABLE)
    _insert_samples(subset, table)


def lambda_handler(event, context) -> None:
    """
    AWS Lambda entry point.

    :param event: The event that triggered this execution.
    :param context: Current runtime information: http://docs.aws.amazon.com
                    /lambda/latest/dg/python-context-object.html.
    """
    logger.info(f'Event: {event}')
    _timely_execution_check(event, context)
    main()
