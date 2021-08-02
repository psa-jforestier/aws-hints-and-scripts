# EMAIL TO SLACK

This function is used to forward an email to a Slack channel. Usefull when a provider do not have a Slack connector.

Written in Python3.

## Prerequisits

Allow this AWS account to handle email reception :
- SES must be enabled with a validated domain name for receiving email.
- in SES, create a Rule Set on receiving email.
  - create a rule with "recipients = slack-bot@yourdomain.com"
  - actions : S3 in bucket (use a prefix named slack-bot@yourdomain.com so all your email will be stored is s3/slack-bot@yourdomain.com) + invoke this Lambda function


Any email send to slack-bot@yourdomain.com and to slack-bot+WHATEVER@yourdomain.com will trigger this Lambda.

For each Slack Channel :
- enable webhook on Slack 
- modify the settings.json file with to add an element named with the email address slack-bot+WHATEVER@yourdomain.com and associated to the webhook URL.
- configure your alert provider to send an email to slack-bot+WHATEVER@yourdomain.com
