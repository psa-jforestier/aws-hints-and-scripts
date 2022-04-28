#!/usr/bin/python3
# -*- coding: latin-1 -*-
from datetime import datetime
import pprint
import random
import time


def isMatchOpeningHours(openinghours, currentDay, currentHours):
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
  pprint.pprint(oh_table)
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
          print("Matching day ", day, " current hour ", hour)
          day_hour_table = [x.strip() for x in value.split('-')]
          start = day_hour_table[0]
          stop = day_hour_table[1]
          print("start ", start," stop ", stop)
          if (stop == hour or stop == '*'):
            action = 'stop'
          if (start == hour or start == '*') :
            action = 'start'

  return action
        
#openinghours = "*:8-20;Fri:-20;Sat:-*;Sun:-*;TZ:Europe/Paris"
#openinghours = "*:-* # Arreter toutes les heures".lower()
#openinghours = "Mon:8-20;Tue:-14;Wed:-20;Thu:8-;Fri:-20;TZ:UTC".lower()
#openinghours = "*:8-20;Sat:-*;Sun:-*;TZ:UTC".lower()
openinghours = "tue:10-15;tz:europe/paris".lower()

currentHours = ["12 utc", "20 europe/paris", "11 tz/unkown"]
nowDay = "tue"

action = isMatchOpeningHours(openinghours, nowDay, currentHours)
print(action)
