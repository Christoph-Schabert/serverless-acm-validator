import datetime
import hashlib
import json
import os
import sys
import time
import traceback
from datetime import date, datetime

import boto3
from botocore.vendored import requests

#https://www.reddit.com/r/aws/comments/8g1vhq/cloudformation_create_and_verify_acm_certificate/

acm = boto3.client('acm')
    

def create_acm_certificate(event, context):
    domain_name = event['ResourceProperties']['DomainName']
    subject_alternative_names = event['ResourceProperties'].get('SubjectAlternativeNames', [])
    subject_alternative_names.append(domain_name)
    
    #If domain names are to long a way to reduce
    if len(domain_name) > 62:
        hashlen = 62-len(os.environ['Domain'])
        ch = hashlib.sha256(domain_name).hexdigest()[-hashlen:]
        domain_name = "%s.%s" % (ch, os.environ['Domain'])
      
    response = acm.request_certificate(
        DomainName=event['ResourceProperties']['DomainName'],
        ValidationMethod="DNS",
        IdempotencyToken=event['LogicalResourceId'],
        SubjectAlternativeNames= subject_alternative_names
     )
    cert_arn = response['CertificateArn']
    event['PhysicalResourceId'] = cert_arn
    event['Data'] ={
        "CertificateArn": cert_arn
    }
    return event

def validates_acm_via_dns(event, context):
    r53 = boto3.client('route53')
    response = acm.describe_certificate(
        CertificateArn=event['PhysicalResourceId']
    )   
    r53_content = []
    for vo in response['Certificate']['DomainValidationOptions']:
        rr = vo['ResourceRecord']
        r53_content.append({'Action':'UPSERT','ResourceRecordSet':{'Name': rr['Name'],'Type': rr['Type'],'TTL': 3600,'ResourceRecords': [{'Value': rr['Value']}]}})   
    response = r53.change_resource_record_sets(
            HostedZoneId=os.environ['HOSTED_ZONE_ID'],
            ChangeBatch={'Comment':'Auth','Changes':r53_content}
    )
    return event

def status_acm_certificate(event, context):
    response = acm.describe_certificate(
    CertificateArn=event['PhysicalResourceId']
)   
    return response['Certificate']['Status']

def delete_acm_certificate(event, context):
    response = acm.delete_certificate(
            CertificateArn=event['PhysicalResourceId']
    )
    del event['PhysicalResourceId']
    return event
