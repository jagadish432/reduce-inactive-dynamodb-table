import logging


# Initialize the logger object
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def remediateWaste(table_info, dynamodb_client):
    logger.info(f"validating remediate waste on table - {table_info['TableName']}")
    table_info['Action'] = 'NO_ACTIONS_AVAILABLE'

    if table_info['TableStatus'] == 'ACTIVE' and table_info['CapacityMode'] == 'Provisioned' \
        and table_info['IsCreatedBeforeHistoryDate'] and table_info['IsUnused']:
        enableOnDemandMode(table_info['TableName'], dynamodb_client)
        table_info['Action'] = 'ENABLED_ON_DEMAND_MODE'

    return table_info


def enableOnDemandMode(table_name, dynamodb_client):
    logger.info(f"updating table - {table_name} to On-Demand I/O mode")
    response = dynamodb_client.update_table(
        TableName = table_name,
        BillingMode = 'PAY_PER_REQUEST'
    )
