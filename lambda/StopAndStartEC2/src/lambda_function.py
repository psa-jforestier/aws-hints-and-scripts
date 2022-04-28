#!/usr/bin/python3
# -*- coding: latin-1 -*-
'''
A function to start and stop EC2 instances of all accounts attached to the organization.
See https://github.com/D4UDigitalPlatform/cloudscripts/tree/master/aws/scripts/lambda/StopAndStartEC2/Organization

Each instances to stop or stap must have a tag named "openinghours" with a string value like "Mon:8-20;Tue:-20;TZ:Europe/Paris...#..." :
- Dayname (Mon, Tue, ..., * for all day)
- :
- StartHour-StopHour : (from 0 to 23 or * for every hour)
- TZ : a string with the Time Zone ("UTC" or "Europe/Paris")
- # a comment
Lambda Settings : runtime is Python 3, max memory is 128Mb, max exec time : 1mn
/!\ This lambda will call itself asynchronously for each account of the organization
Env Var :
API_RETRY_ATTEMPTS : mandatory, set it to "10" to indicate number of retry when calling any AWS api
EXCLUDE_ACCOUNTS : optional, list of account id or account name separated  by a ; . A comment starting with # may be at the end of the line
DRY_RUN : mandatory : set it to "True" to not start or stop instances, or "False" to effectively act on instances
'''
import boto3
import logging
import time
import os
import pprint
import json
from botocore.exceptions import ClientError
from time import gmtime, strftime
from datetime import datetime,timezone
from configure_profile import ConfigureAccount
from StopAndStartEC2_manager import StopAndStartEC2Manager
from dateutil import tz

MASTER_ACCOUNT = 'REPLACE IT WITH YOUR MASTER ACCOUNT ID'
MASTER_ACCOUNT_ROLE = 'orga-stopandstartec2master-role'
CHILD_ACCOUNT_ROLE = 'orga-stopandstartec2-from-secu'

def printf(format, *args):
  print(format % args )

# Main lambda function
# If event contains an 'Account' object, it will stop/start ec2 on this account.
# If not, the lambda search for all accounts of the organization and call itself with an Account object
def lambda_handler(event, context):
  DRY_RUN = os.getenv('DRY_RUN')
  if (DRY_RUN == None):
    raise ValueError('Set the DRY_RUN env var to True or False before running the Lambda')
  if ("Account" in event):
    # If the event contains an Account, it is an asychronous call from this very self lambda
    excluded = os.getenv('EXCLUDE_ACCOUNTS') # list of id / name separated with ;
    exclude = False
    if (excluded != None):
      excluded = [x.strip() for x in excluded.split(';')]
      if ( event['Account']['Id'] in excluded
        or event['Account']['Name'] in excluded):
          printf("This account is in the exclude list of account in EXCLUDE_ACCOUNTS, nothing to do\n")
          exclude = True
      else:
        exclude = False
    if (not exclude):
      StopAndStartEC2ForOneAccount(
          event['Account']['Id'],
          event['Account']['Name'],
          event['Account']['Role'],
          event['Account']['SessionName'],
          event['HourUTC'],
          event['HourEP'],
          event['Day'])
      return True
  else:
    StopAndStartEC2()
  return True

def StopAndStartEC2ForOneAccount(accountId, accountName, role, sessionName, nowUtc, nowEP, nowDay):
  printf("*** Working with EC2 on account %s %s. Looking for instance at %d UTC, %d Europe/Paris day %s\n", accountName, accountId, nowUtc, nowEP, nowDay)
  accountSession = ConfigureAccount().assume_role(
    accountId,
    CHILD_ACCOUNT_ROLE,
    accountId + '_account_session'
  )
  StopAndStartEC2Manager(accountSession, accountName, isChildAccount=True).StopAndStartEC2(nowUtc, nowEP, nowDay.lower())
  return True
  
def StopAndStartEC2():
  lambdaClient = boto3.client('lambda')
  nowUtc = datetime.now(timezone.utc) # Current time in UTC
  nowEP = nowUtc.astimezone(tz.gettz('Europe/Paris') ) # Current time for timezone Paris
  nowLocal = nowUtc.astimezone(tz.tzlocal()) # Current loal time for this server (depends of AWS region)
  nowDay = nowUtc.strftime("%a")
  printf("UTC=%s ; Europe/Paris=%s ; Local = %s\n", nowUtc, nowEP, nowLocal)  
  print("  Current hour in utc   = ", nowUtc.hour)
  print("  Current hour in Paris = ", nowEP.hour)
  print("  Current day = ", nowDay)
  printf("Get all accounts of this organization :\n")
  masterSession = ConfigureAccount().assume_role(
    MASTER_ACCOUNT, 
    MASTER_ACCOUNT_ROLE, 
    'master_account_session'
  )
  accountList = GetAccountList(masterSession)
  accountList.sort(key = lambda x: x['Name'].lower(), reverse=False)
  printf("got %d accounts\n", len(accountList))
  for account in accountList:
    printf("Account %s : %s : \n", account['Id'], account['Name'])
    if account['Status'] != 'ACTIVE':
      printf("  Inactive account, skip.\n")
    else:
      try:
        
        printf("Call async lambda\n")
        params = {
          "Account":{"Name": account['Name'], "Id" :  account['Id'], "Role":CHILD_ACCOUNT_ROLE, "SessionName":account['Id'] + '_account_session'},
          "HourUTC" : nowUtc.hour, "HourEP" : nowEP.hour, "Day" : nowDay
        }
        # This lambda calls itself so it is not necessary to setup a dedicated lambda.
        # Recrusion is handled by the params (received in the "event" params of the lambda)
        
        response = lambdaClient.invoke(
          FunctionName = 'arn:aws:lambda:eu-west-1:910695705412:function:StopAndStartEC2',
          InvocationType = 'Event',
          Payload=json.dumps(params)
          )
        printf("Lambda called, StausCode=%d\n", response['StatusCode'])

      except ClientError as error:
        print("\r\n/!\\ ERROR :")
        print(error)
        print("\n")
        pass


def GetAccountList(masterSession):
  """
    Get the list the AWS accounts in the organization
    format
        {
            'Id': 'string',
            'Arn': 'string',
            'Email': 'string',
            'Name': 'string',
            'Status': 'ACTIVE'|'SUSPENDED',
            'JoinedMethod': 'INVITED'|'CREATED',
            'JoinedTimestamp': datetime(2015, 1, 1)
        }
  """
  organization_client = masterSession.client('organizations')
  accountList = []
  tempAccountList = organization_client.list_accounts()
  accountList.extend(tempAccountList['Accounts'])
  nextToken = None
  if 'NextToken' in tempAccountList:
    nextToken = tempAccountList['NextToken']
  while nextToken:
    tempAccountList = organization_client.list_accounts(NextToken=nextToken)
    accountList.extend(tempAccountList['Accounts'])
    if 'NextToken' in tempAccountList:
      nextToken = tempAccountList['NextToken']
    else:
      break
  
  return accountList