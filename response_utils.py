from http import HTTPStatus
import datetime
import json


def myconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


def build_http_response(status_code: HTTPStatus = HTTPStatus.OK, response_body={}):
    event = {
        'statusCode': status_code.value,
        'body': json.dumps(response_body, default=myconverter)
    }
    return event