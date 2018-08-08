import json
import logging
import os
from urllib.request import HTTPHandler, Request, build_opener

import boto3
from botocore.exceptions import ClientError

FAILED = 'FAILED'
SUCCESS = 'SUCCESS'

def send_signal(event, response_status, reason):
    response_body = json.dumps(
        {
            'Status': response_status,
            'Reason': str(reason or 'ReasonCanNotBeNone'),
            'PhysicalResourceId': event.get('PhysicalResourceId', event['LogicalResourceId']),
            'StackId': event['StackId'],
            'RequestId': event['RequestId'],
            'LogicalResourceId': event['LogicalResourceId'],
            'Data': event.get('Data', {})
        },
        sort_keys=True,
    ).encode('utf8')
    logging.debug(response_body)
    opener = build_opener(HTTPHandler)
    request = Request(event['ResponseURL'], data=response_body)
    request.add_header('Content-Type', '')
    request.add_header('Content-Length', len(response_body))
    request.get_method = lambda: 'PUT'
    opener.open(request)

def start_custom_resource(event, context):
    resource_type = event.get('ResourceType',"Custom::Unknown").split('::')[1].lower()
    step_function_arn = "arn:aws:states:{region}:{account_id}:stateMachine:{stack_name}-{resource_type}".format(
        region=os.environ['AWS_DEFAULT_REGION'], account_id = os.environ['ACCOUNT_ID'], resource_type=resource_type, stack_name = os.environ['STACK_NAME']
    ) 
    name = "{stack_id}-{request_id}".format(
        stack_id= event.get('StackId','/UnknownStackId/').split('/')[1][:33] ,
        request_id=event.get('RequestId','UnknownRequestId'))
    try:
        client = boto3.client('stepfunctions')
        client.start_execution(stateMachineArn=step_function_arn, name=name, input=json.dumps(event))
    except ClientError as ex:
        logging.exception(event)
        if ex.response['Error']['Code'] == "StateMachineDoesNotExist":   
            send_signal(event, FAILED, "Unknown Resource %s" % resource_type)
        elif ex.response['Error']['Code'] not in ["ExecutionAlreadyExists"]:
            send_signal(event, FAILED, str(ex))
        return ex.response
def send_failed_signal(event, context):
    message = '{error_name}: {cause}'.format(error_name=event.get('ErrorObject', {}).get('Error', "Unknown"), cause=event.get('ErrorObject', {}).get('Cause'))
    send_signal(event, FAILED, message)
    return {'status': FAILED, 'message': message}


def send_success_signal(event, context):
    send_signal(event, SUCCESS, None)
    return {'status': SUCCESS, 'message': None}
