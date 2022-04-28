#!/usr/bin/python3
# -*- coding: latin-1 -*-
import time
import boto3
import json


class ConfigureAccount:
  def __init__(self):
    self._sts_client = boto3.client('sts')


  def assume_role(self, account_id, role, session_name = 'lambda_account_automation_session'):
    role_arn = "arn:aws:iam::" + account_id + ":role/" + role
    print ("role to assume : " + role_arn)
    response = self._sts_client.assume_role(
       RoleArn=role_arn,
         RoleSessionName=session_name
         )
    session = boto3.Session(
      aws_access_key_id=response['Credentials']['AccessKeyId'],
      aws_secret_access_key=response['Credentials']['SecretAccessKey'],
      aws_session_token=response['Credentials']['SessionToken']
    )
    return session

