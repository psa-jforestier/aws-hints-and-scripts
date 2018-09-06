#!/usr/bin/env python
# -*- encoding: utf-8
# Based on https://alexwlchan.net/2017/11/fetching-cloudwatch-logs/
"""Print log event messages from a CloudWatch log group.
"""
import pprint
import argparse
import boto3
import sys # to use sys.stdout
import os
from datetime import datetime
import calendar
from dateutil import parser # install it with : pip install python-dateutil
import sys
import time

def printf(format, *args):
    sys.stdout.write(format % args)

# Remove console output buffuring, usefull when running in Cygwin Bash.
buf_arg = 0
if sys.version_info[0] == 3:
    os.environ['PYTHONUNBUFFERED'] = '1'
    buf_arg = 1
try:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'a+', buf_arg)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'a+', buf_arg)
except:
    pass

parser = argparse.ArgumentParser(
    description='Print log event messages from a CloudWatch log group.',
    epilog='TIMESTAMP can be in UTC Unix Epoch milliseconds, or in UTC string like "2010-12-31T12:34:56.789". If start is after end, events are displayed in reverse order (from sooner to later).')
parser.add_argument('--start', metavar='TIMESTAMP', dest='startTime', required=False,
    help='Only print events with a timestamp after this time.')
parser.add_argument('--end', metavar='TIMESTAMP', dest='endTime', required=False,
    help='Only print events with a timestamp before this time.')
parser.add_argument('-f', dest='follow', action='store_true', required=False,
    help='Display events in follow mode.', default=False)
parser.add_argument('--verbose', dest='verbose', action='store_true', required=False,
    help='Print more debug information.', default=False)
parser.add_argument('--wait', metavar='N', dest='waittime', required=False, type=float,
    help='Wait time (in s) before getting events in follow mode (use with -f). Default %(default)s', default=5)
parser.add_argument('log_group', nargs=1, metavar='LOGGROUP',
    help='The name of the log group' )
parser.add_argument('log_stream', nargs=1, metavar='LOGSTREAM',
    help='The name of the log stram' )
args = parser.parse_args()

epoch = datetime(1970, 1, 1)
p = '%Y-%m-%dT%H:%M:%S.%f'
log_group = args.log_group[0]
log_stream = args.log_stream[0]

startTime = args.startTime
endTime = args.endTime

client = boto3.client('logs')

kwargs = {
        'logGroupName': log_group,
        'logStreamName': log_stream,
        'limit': 10000,
        'startFromHead': True
}
startTime_ts = endTime_ts = None
if (args.follow == True):
    kwargs['startTime'] = startTime_ts = int(1000*time.time())
if (startTime != None):
    startTime_ts = int(1000*(datetime.strptime(startTime, p) - epoch).total_seconds())
    kwargs['startTime'] = startTime_ts
if (endTime != None):
    endTime_ts = int(1000*(datetime.strptime(endTime, p) - epoch).total_seconds())
    kwargs['endTime'] = endTime_ts
if (startTime != None and endTime != None):
    if (startTime_ts > endTime_ts):
        kwargs['startFromHead'] = False
        kwargs['startTime'] = endTime_ts
        kwargs['endTime'] = startTime_ts

if (args.verbose == True):
    printf("Gettings events from %s to %s\n", startTime_ts, endTime_ts)

while True:
    resp = client.get_log_events(**kwargs)
    events = resp['events']
    nbevents = len(events)
    if (nbevents > 0):
        ev_first = events[0]
        ev_last = events[nbevents - 1]
        for ev in events:
            print ev['message'].encode('utf-8')
    if (resp['nextBackwardToken'][2:] == resp['nextForwardToken'][2:]) and (args.follow == False):
        break
    kwargs['nextToken'] = resp['nextForwardToken']
    
    if (args.verbose == True):
        if (nbevents == 0):
            printf("Got 0 event...\033[K\r")
        else:
            duration = ev_last['timestamp'] - ev_first['timestamp']
            printf("Got %d events in a duration of %s ms (%.3f ev/s)...\033[K\r", 
                nbevents, duration, 
                1000.0 * nbevents / duration if (nbevents != 0) else 0
                )
        
    if (args.follow == True):
        time.sleep(args.waittime)
