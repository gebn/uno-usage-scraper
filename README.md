# Uno Usage Scraper

[![Build Status](https://travis-ci.org/gebn/uno-usage-scraper.svg?branch=master)](https://travis-ci.org/gebn/uno-usage-scraper)

An AWS Lambda function that retrieves and stores hourly usage data for an uno
Communications Ltd. line. It should run at 12-hour intervals; the exact time
doesn't matter, but it must not vary with daylight saving.

For me, it is currently set to run at (UTC):

 - 08:30 (scrape 09:00 through 20:00 yesterday)
 - 20:30 (scrape 21:00 yesterday through 08:00 today)

This translates to a CloudWatch Events cron expression schedule of
`30 8,20 * * ? *`.

## Configuration

Uno's portal is hosted in Reading, so eu-west-2 or eu-west-1/eu-central-1 are
the best AWS regions from a latency perspective.

| Parameter | Value                   |
|-----------|-------------------------|
| Runtime   | Python 3.6              |
| Handler   | `main.lambda_handler`   |
| Memory    | 128 MiB (only uses ~42) |
| Timeout   | 10 seconds              |

## Environment Variables

The function expects the following to be defined:

| Name                       | Description                                                                                                                                                                                                    |
|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `UNO_PRODUCT_ID`           | The ID of the product being measured. This can be found at the end of the URL on the daily usage summary for the line.                                                                                         |
| `UNO_COOKIE`               | The value of your `WHMCSUser` cookie, used to authenticate the function to Uno's portal.                                                                                                                       |
| `UNO_COOKIE_EXPIRES`       | When `UNO_COOKIE` expires, as an ISO 8601 date. Warnings will be sent starting two weeks before the cookie expires.                                                                                            |
| `UNO_COOKIE_WARNINGS`      | Whether to enable cookie expiry warnings. Defaults to true; set to an empty string to disable.                                                                                                                 |
| `DYNAMO_TABLE`             | The name of the DynamoDB table to store results in (N.B. this is assumed to exist in the same region as the function). This function must have `dynamodb:BatchWriteItem` and `dynamodb:PutItem` for the table. |
| `NOTIFICATION_TOPIC_ARN`   | The SNS topic to send all notifications to, hopefully with [pushover-notification](https://github.com/gebn/pushover-notification) subscribed to it. This function must have `sns:Publish`.                     |
| `USAGE_PUSHOVER_APP_TOKEN` | The Pushover application token to send usage summaries as.                                                                                                                                                     |
| `SEND_USAGE`               | Whether to enable usage summaries for the scraped period each function execution. Defaults to false; set to any non-empty string to enable.                                                                    |
