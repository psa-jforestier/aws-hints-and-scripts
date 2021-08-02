#!/usr/bin/python
# -*- coding: latin-1 -*-
"""
This lambda function is used to transfert email to a Slack channel. 

Email are received by SES and forwrded to S3 and this Lambda.
Then this lambda read the email address, map it to a Slack Webhook (in settings.json), then read the plain-text mail content and post it to the Slack channel.

The role associated to this lambda must have :
- S3 read
- CloudWrite write

"""


import json
import pprint
import os
import json
import boto3
import urllib.request
from datetime import datetime
from dateutil import tz
import email

s3_client = boto3.client('s3')

def printtolog(message):
    print(datetime.now().strftime("[ %H:%M:%S.%f ]") + message)
    
def getEmailMsg(mail):
  msg = email.message_from_string(mail)
  for part in msg.walk():
    print(part.get_content_type())
    if part.get_content_type() == 'text/plain':
      parts = (part.get_payload(decode=True))
      return msg['subject'].replace('\n', ''), parts.decode(errors="ignore")
  return msg['subject'].replace('\n', ''),msg['body']
            
def handle_record(record, settings, context):
    """ Handle a Lambda record
    """
    s3bucket = settings['s3bucket']
    s3prefix = settings['s3prefix']
    if (record.get('ses') == None):
        printtolog("Warning : no ses record found")
        return
    slacksettings = None
    for emailaddr in record['ses']['mail']['destination']:
        slacksettings = settings['Slack'].get(emailaddr)
        if (slacksettings == None):
            printtolog("WARNING : email "+ emailaddr + " is not configured in settings.json")
        else:
            break
    if (slacksettings == None):
        printtolog("ERROR : None of the email above match a configuration in settings.json")
        raise SystemExit(1)
    messageId = record['ses']['mail']['messageId']
    print("Receiving email from " + emailaddr + " with msg id " + messageId)
    download_path = '/tmp/'+messageId
    print("  Forward message to Slack webhook " + slacksettings['webhook'])
    print("  Read email from S3 s3://" + s3bucket + "/"+s3prefix+messageId + " and save it to " + download_path)
    s3_client.download_file(s3bucket, s3prefix+messageId, download_path)
    
    # Decode incomming email
    rawtext = open(download_path).read()
    subject, msg = getEmailMsg(rawtext)
    
    # Prepare slack msg
    slack_data = {
        "text": subject,
        "blocks": [
            {
                "type": "header",
    			"text": {
    				"text": subject,
    				"type": "plain_text"
    			},
    		
    		},
    		{
			    "type": "context",
			    "elements": [
    				{
    					"type": "plain_text",
    					"text": "Email posted to " + emailaddr + " and  fowarded to this channel by Lambda " + context.invoked_function_arn
    				}
    			]
	    	},
    		{
    			"type": "section",
    			"text" : {
    			    "type": "mrkdwn",
    			    "text": "```"+msg[0:1900]+"```"
    			}
    		},
    		{
    			"type": "section",
    			"text": {
    				"type": "mrkdwn",
    				"text": "_The message is truncated at 2000 caracters_"
			}
		}
        ]
    }


    req = urllib.request.Request(slacksettings.get('webhook'))
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    jsondata = json.dumps(slack_data)
    jsondataasbytes = jsondata.encode('utf-8')   # needs to be bytes
    req.add_header('Content-Length', len(jsondataasbytes))
    response = urllib.request.urlopen(req, jsondataasbytes)

    pprint.pprint(response)
    
    
def lambda_handler(event, context):
    pprint.pprint(event)
    if (os.path.isfile("settings.json") == False):
        printtolog("ERROR : settings.json file is not readable")
        raise SystemExit(1)
    with open("settings.json") as json_data:
        settings = json.load(json_data)
    for num, record in enumerate(event['Records']):
        printtolog(" Handling record No " + str(num))
        handle_record(record, settings, context)
    #pprint.pprint(event)
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
