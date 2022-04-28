#!/usr/bin/python

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import logging
from time import gmtime, strftime
import time
from time import sleep
import datetime
import os
import csv
import pprint

import multiprocessing as mp

OPS_GROUP = 'GroupePSA_Ops'

def printf(format, *args):
  print(format % args,end='' )

# Return the value of a KVarray. The KVarray is  [{'Key': 'k1', 'Value': 'v1'}, {'Key': 'k2', 'Value': 'v2s'}, ... ]
def getValueFromKey(KVarray, keyName, notfound = None):
  for kv in KVarray:
    if kv['Key'] == keyName:
      return kv['Value']
  return notfound
  

class StopAndStartEC2Manager:
  """
    TODO this comment
  """

  def __init__(self, session, accountName, isChildAccount):
    # the API GenerateCredentialReport often reaches the throttling limit. 
    # Raise the number of retry attempts 
    self._config = Config(
      retries = {
        'max_attempts': int(os.environ['API_RETRY_ATTEMPTS']),
        'mode': 'standard'
      },
      region_name = 'us-east-1' # init with global region
    )
    
    self._iam_client = session.client('iam', config=self._config)
    self._iam_resource = session.resource('iam')
    self._ec2_client = session.client('ec2', config=self._config)
    self._account_name = accountName
    self._isChildAccount = isChildAccount
    self._session = session
    
    # allowUserUpdate is false for child accounts because sometimes accesskey are used for the CICD 
    # if we delete it, it will break the CICD.      
    self._allowUserUpdate = not isChildAccount
    # if we call GetCredentialReport for all accounts, we reach the AWS throttling limit
    # so only SecuCDF and master account
    self._useCredentialReport = not isChildAccount
    self._userCredentialWarningList = []
    
  def StopAndStartEC2(self, nowUtc, nowEP, nowDay):
    DRY_RUN = os.getenv('DRY_RUN').lower() == 'true'
    regions = self._ec2_client.describe_regions()['Regions']
    printf("  Found %d regions\n", len(regions))
    currentHour = [str(nowUtc) + " utc", str(nowEP) + " europe/paris"]
    instances = self.getInstancesToBeStartedOrStoped(regions)
    printf(" Found %d tagged instances\n", len(instances))
    if (len(instances) > 0):
      # Prepare a list of instances to be stopped and started
      toStart = []
      toStop = []
      for instance in instances:
        #timetostart = getValueFromKey(instance['Tags'], 'timetostart', "").lower()
        #timetostop = getValueFromKey(instance['Tags'], 'timetostop', "").lower()
        timetostart = timetostop = None # do not rely on this tags, only use the openinghours tag
        openinghours = getValueFromKey(instance['Tags'], 'openinghours', "").lower()
        printf("%s instance %s %s : start %s ; stop %s ; %s\n",  instance['RegionName'], instance['InstanceId'], instance['State'], timetostart, timetostop, openinghours)
        matchOpeningHours = self.isMatchOpeningHours(openinghours, nowDay, currentHour)
        if instance['State'] == 'stopped':
          # Should I start ?
          if (timetostart in currentHour or matchOpeningHours == 'start'):
            toStart.append(instance)
        elif instance['State'] == 'running':
          # Should I start ?
          if (timetostop in currentHour or matchOpeningHours == 'stop'):
            toStop.append(instance)
      printf("=== START INSTANCES ===\n")
      for i in toStart:
        printf("%20s | %-16s | %-16s | %s\r\n", i['InstanceId'], i['RegionName'], i['InstanceType'], i['InstanceName'])
        self._config.region_name = i['RegionName']
        self._ec2_client = self._session.client('ec2', config=self._config)
        if (DRY_RUN) :
          printf("Dry run mode : start_instances(%s) ignored\n", i['InstanceId'])
        else:
          res = self._ec2_client.start_instances(InstanceIds=[i['InstanceId']])
      printf("=== STOP INSTANCES ===\n")
      for i in toStop:
        printf("%20s | %-16s | %-16s | %s\r\n", i['InstanceId'], i['RegionName'], i['InstanceType'], i['InstanceName'])
        self._config.region_name = i['RegionName']
        self._ec2_client = self._session.client('ec2', config=self._config)
        if (DRY_RUN) :
          printf("Dry run mode : stop_instances(%s) ignored\n", i['InstanceId'])
        else:
          res = self._ec2_client.stop_instances(InstanceIds=[i['InstanceId']])
    return
  
  # Return all instances in run or stopped with a proper timetostop or timetostart tag
  def getInstancesToBeStartedOrStoped(self, regions):
    i = []
    for region in regions:
      self._config.region_name = region['RegionName']
      self._ec2_client = self._session.client('ec2', config=self._config)
      #printf("Search for instances in region %s\n", self._config.region_name)
      try:
        instances = self._ec2_client.describe_instances(
          Filters = [
            {'Name':'tag-key','Values':["timetostop", "timetostart", "openinghours"]},
            {'Name':'instance-state-name','Values':["running","stopped"]}
          ])
        for inst in instances['Reservations']:
          for j in inst['Instances']:
            name = getValueFromKey(j['Tags'], 'Name')
            theInstance = {
              u'RegionName':region['RegionName'],
              u'InstanceType' :j['InstanceType'],
              u'InstanceId' :j['InstanceId'],
              u'InstanceName' : name,
              u'State' : j['State']['Name'],
              u'Tags' : j['Tags']
              
            }
            i.append(theInstance)
            
      except self._ec2_client.exceptions.ClientError as error:
        print("ERROR in Region", self._config.region_name, error)
        pass
    return i
  '''  
  def StopInstancesAt(self, hours, regions):
    print("=== STOP INSTANCES ===")
    print("Here are the running EC2 instance that must be stopped at ",hours)
    instances = self.listEc2ToStopAt(hours, regions)
    instanceIds = []
    for i in instances:
      printf("%20s | %-16s | %-16s | %s\r\n", i['InstanceId'], i['RegionName'], i['InstanceType'], i['InstanceName'])
      self._config.region_name = i['RegionName']
      self._ec2_client = self._session.client('ec2', config=self._config)
      res = self._ec2_client.stop_instances(InstanceIds=[i['InstanceId']])
      
  def StartInstancesAt(self, hours, regions):
    print("=== START INSTANCES ===")
    print("Here are the stopped EC2 instance that must be started at ",hours)
    instances = self.listEc2ToStartAt(hours, regions)
    instanceIds = []
    for i in instances:
      printf("%20s | %-16s | %-16s | %s\r\n", i['InstanceId'], i['RegionName'], i['InstanceType'], i['InstanceName'])
      self._config.region_name = i['RegionName']
      self._ec2_client = self._session.client('ec2', config=self._config)
      res = self._ec2_client.start_instances(InstanceIds=[i['InstanceId']])
  '''  
  '''
  def listEc2ToStopAt(self, hours, regions):
    instances = []
    i = self.listEc2HavingThisTagKeyAndState('timetostop', 'running', regions)
    for inst in i:
      for j in inst['Instances']:
        instanceName = None
        timeToStop = None
        for k in j['Tags']:
          if k['Key'] == 'Name':
            instanceName = k['Value']
          elif k['Key'] == 'timetostop':
            timeToStop = k['Value'].strip()  
        aInstance = {
          'InstanceId':j['InstanceId'],
          'InstanceType':j['InstanceType'],
          'InstanceName':instanceName,
          'TimeToStop':timeToStop,
          'RegionName':inst['RegionName']
        }
        if (timeToStop in hours):
          instances.append(aInstance)
    return instances
  
  def listEc2ToStartAt(self, hours, regions):
    instances = []
    i = self.listEc2HavingThisTagKeyAndState('timetostart', 'stopped', regions)
    for inst in i:
      for j in inst['Instances']:
        instanceName = None
        timeToStart = None
        for k in j['Tags']:
          if k['Key'] == 'Name':
            instanceName = k['Value']
          elif k['Key'] == 'timetostart':
            timeToStart = k['Value'].strip()
        aInstance = {
          'InstanceId':j['InstanceId'],
          'InstanceType':j['InstanceType'],
          'InstanceName':instanceName,
          'TimeToStart':timeToStart,
          'RegionName':inst['RegionName']
        }
        if (timeToStart in hours):
          instances.append(aInstance)
    return instances
  '''
  
  '''
  def listEc2HavingThisTagKeyAndState(self, key, state, regions):
    # state : pending | running | shutting-down | terminated | stopping | stopped
    
    i = []
    
    #pool = mp.Pool(4)
    #results = pool.starmap(self.listEc2HavingThisTagKeyAndStateForOneRegion, [(self, key, state, r) for r in regions])
    #pool.close()
    #pprint.pprint(results)
    for r in regions:
      instances = self.listEc2HavingThisTagKeyAndStateForOneRegion(key, state, r['RegionName'])
      for inst in instances:
        i.append(inst)
    return i
  '''
  
  '''
  def listEc2HavingThisTagKeyAndStateForOneRegion(self, key, state, region):
    # state : pending | running | shutting-down | terminated | stopping | stopped
    
    i = []
    self._config.region_name = region
    self._ec2_client = self._session.client('ec2', config=self._config)
    printf("Search for instances in region %s at state %s and a tag named %s:\n", region, state, key)
    try:
      instances = self._ec2_client.describe_instances(
        Filters = [
          {'Name':'tag-key','Values':[key]},
          {'Name':'instance-state-name','Values':[state]}
        ])
      for inst in instances['Reservations']:
        i2 = inst
        i2.update({u'RegionName':region})
        i.append(i2)
        #for j in i2['Instances']:
        #  pprint.pprint(j['InstanceId'])
    except self._ec2_client.exceptions.ClientError as error:
      print("\r\n")
      print(error)
      pass
    return i
'''
  # return "stop" or "start" or None if an openinghours string match the currentDay in the currentHours
  # openinghours : "*:8-20;Sat:-*;Sun:-*;TZ:Europe/Paris # machine start every day except weekend"
  # openinghours : "*:-20;TZ:Europe/Paris # machine stop every day at 20"
  # openinghours : "Mon:8-;Fri:-20;TZ:Europe/Paris # machine start every monday and stop every friday"
  def isMatchOpeningHours(self, openinghours, currentDay, currentHours):
    if (openinghours == None or openinghours == ''):
      return None
    # Convert the string to an array of object
    openinghours = openinghours.split("#", 1)[0] # remove comment
    oh_tokens = [x.strip() for x in openinghours.split(';')]
    oh_tz = 'utc'
    oh_table = []
    for oh in oh_tokens:
      day = oh.split(':')[0]
      value = oh.split(':')[1]
      if (day == 'tz'):
        oh_tz = value
      #oh_table[day] = value
      oh_table.append({'day':day,'value':value})
    #
    action = None
    for hour in currentHours:
      # get TZ of current hour
      hour_split = hour.split()
      hour = hour_split[0].strip()
      if (len(hour_split) == 1):
        tz = "utc"
      else:
        tz = hour_split[1].strip()
      if tz == oh_tz:
        for i in oh_table:
          day = i['day']
          value = i['value']
          if (day == currentDay or day == '*'):
            day_hour_table = [x.strip() for x in value.split('-')]
            start = day_hour_table[0]
            stop = day_hour_table[1]
            if (stop == hour or stop == '*'):
              action = 'stop'
            if (start == hour or start == '*') :
              action = 'start'
    return action