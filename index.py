import logging
import boto3
from datetime import datetime, timedelta, time, date
import pytz
import functools
import os
import json
from http import HTTPStatus

from constants import MAX_NUM_OF_REMEDIATIONS, DAYS_TO_SEARCH_FROM, SNS_ARN
from remediate import remediateWaste
from response_utils import build_http_response, myconverter


DAYS_TO_SEARCH_FROM = os.environ.get('days_to_search_from') or DAYS_TO_SEARCH_FROM
SNS_ARN = os.environ.get('sns_arn') or SNS_ARN

# Initialize the logger object
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize the cloudwatch and dynamodb clients using boto3 SDK
cloudwatch_client = boto3.client('cloudwatch')
dynamodb_client = boto3.client('dynamodb')
sns_client = boto3.client('sns')


def get_existing_tables(limit=100):
    params = {
        "Limit": limit
    }
    response = dynamodb_client.list_tables(**params)
    tables = response['TableNames']

    while 'LastEvaluatedTableName' in response:
        params.update({'ExclusiveStartTableName': response['LastEvaluatedTableName']})
        response = dynamodb_client.list_tables(**params)
        tables.extend(response['TableNames'])

    return tables


def maxDataPoint(data_points):
    return functools.reduce(lambda a, b: a if a > b['Maximum'] else b['Maximum'], data_points, 0)


def getMetricStatistics(table_name, metric_name):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=DAYS_TO_SEARCH_FROM)
    start_date = datetime.combine(start_date, time.min)

    response = cloudwatch_client.get_metric_statistics(
        Namespace='AWS/DynamoDB',
        MetricName=metric_name,
        Dimensions=[
            {
                'Name': 'TableName',
                'Value': table_name
            },
        ],
        StartTime=start_date,
        EndTime=end_date,
        Period= 60*60*24*DAYS_TO_SEARCH_FROM,
        Statistics=[
            'Maximum',
        ],
        Unit='Count'
    )
    max_value = maxDataPoint(response['Datapoints'])
    return max_value


def assess_table(table_name):
    today = datetime.today()
    historical_date = today - timedelta(days=0, hours=0, minutes=10)
    # historical_date = datetime.combine(historical_date, time.min)
    historical_date = pytz.utc.localize(historical_date)
    params = {
        'TableName': table_name
    }
    table_data = dynamodb_client.describe_table(**params)['Table']
    max_consumed_read = getMetricStatistics(table_name, 'ConsumedReadCapacityUnits')
    max_consumed_write = getMetricStatistics(table_name, 'ConsumedWriteCapacityUnits')

    return {
        "TableName": table_name,
        "TableArn": table_data['TableArn'],
        "TableStatus": table_data['TableStatus'],
        "ItemCount": table_data['ItemCount'],
        "CapacityMode": 'On-Demand' if table_data['ProvisionedThroughput']['ReadCapacityUnits'] == 0 else 'Provisioned',
        "CreationDateTime": table_data['CreationDateTime'],
        "IsCreatedBeforeHistoryDate": True if table_data['CreationDateTime'] < historical_date else False,
        "IsEmpty": True if table_data['ItemCount'] == 0 else False,
        "IsUnused":  True if max_consumed_read == 0 and max_consumed_write == 0 else False
    }


def _lambda_handler(event, context):
    existing_tables = get_existing_tables()
    indiv_tables_descriptions = []

    for table in existing_tables:
        indiv_tables_descriptions.append(assess_table(table))

    new_table_status = []
    remediations_count = 0

    for i in range(0, len(indiv_tables_descriptions)):
        result = remediateWaste(indiv_tables_descriptions[i], dynamodb_client)
        if result['Action'] == 'ENABLED_ON_DEMAND_MODE':
            new_table_status.append(result)
            remediations_count += 1
        if remediations_count == MAX_NUM_OF_REMEDIATIONS:
            break

    if len(new_table_status) > 0:
        response = sns_client.publish(
            TopicArn=SNS_ARN,
            Message=json.dumps(new_table_status, default=myconverter)
        )

    return build_http_response(status_code=HTTPStatus.OK, response_body={
        "error": None,
        "result": new_table_status
    })


def lambda_handler(event, context):
    """
    AWS lambda's handler function
    """
    try:
        return _lambda_handler(event, context)
    except Exception as e:
        logger.error(str(e))
        return build_http_response(status_code=HTTPStatus.BAD_REQUEST, response_body={
            "error": f'Error encountered - {str(e)}',
            "result": None
        })


if __name__ == '__main__':
    response = lambda_handler(None, None)
    import pprint
    pprint.pprint(response)
