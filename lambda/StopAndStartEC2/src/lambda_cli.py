#!/usr/bin/python3
# -*- coding: latin-1 -*-

'''
Wrapper to trigger the lambda function
Parameter : --event "{json:string}"
Start with $> python -u lambda_cli.py
  -u is to have an unbuffered console output
'''

from datetime import datetime
from lambda_function import lambda_handler
import time
import argparse
import pprint
import json

parser = argparse.ArgumentParser(description='Call the Lambda function.')
parser.add_argument('--event', dest='event', action='store', default=None, 
  help='JSON string of the event parameter')
args = parser.parse_args()

context = None
if (args.event != None):
  event = json.loads(args.event)
else:
  event = None
  
NOW = int(round(time.time() * 1000))
print("%s START RequestId: <none> Version: <none>" % datetime.now())
#
res = lambda_handler(event, context)

EXECTIME = int(round(time.time() * 1000)) - NOW
print("%s END RequestId: <none> in %d ms" % (datetime.now() , EXECTIME ))