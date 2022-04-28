# Stop And Start EC2 at scheduled time

A function to start and stop EC2 instances of all accounts attached to the organization.
This is *experimental*. This code work in our organization, but I had to hide some information to publish the code. You have to adapt it.

Each instances to stop or stap must have a tag named "openinghours" with a string value like "Mon:8-20;Tue:-20;TZ:Europe/Paris...#..." :
- `Dayname` (Mon, Tue, ..., * for all day)
- `:`
- `StartHour-StopHour` : (from 0 to 23 or * for every hour)
- `TZ` : a string with the Time Zone ("UTC" or "Europe/Paris")
- `#` a comment

# Lambda installation

Lets say you have a SECU account (with account id is SECU_ID), separated from the MASTER account. The master define an organization, and SECU is a member of this organization. Other accounts also exists and are members of the organization defined in MASTER.

Install the Lamnda on the SECU account :

Lambda Settings : runtime is Python 3, max memory is 128Mb, max exec time : 1mn

Lambda permission : 
The role of the Lambda must have the following policies :
- `AWSLambdaBasicExecutionRole` and `AWSLambdaRole` : two AWS managed policies
- a custom inline role with :
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowLambdaInvocation",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunctionUrl",
                "lambda:InvokeFunction",
                "lambda:InvokeAsync"
            ],
            "Resource": "*"
        }
    ]
}
```

- On each accounts members of the organization (including the MASTER and the SECU), create a role named `orga-stopandstartec2-from-secu` with an Inline policy named `DoActionsOnEC2`
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
                "ec2:StartInstances",
                "ec2:StopInstances"
            ],
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
```
Also, add a Trust relation with the SECU account :
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::SECU_ID:root" <--- replace it
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```
You can use the file ChildAccountRole.yml (review it before launching it in CloudFormation).

- On the MASTER account, create a role named `orga-stopandstartec2master-role` with an inline policy named `ListOrganizationAccounts` :
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "organizations:ListAccounts"
            ],
            "Resource": "*",
            "Effect": "Allow"
        }
    ]
}
```
Also, add a Trust relation with the SECU account :
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::SECU_ID:root" <--- replace it
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

- Edit the `lambda_function.py` code and modify the `MASTER_ACCOUNT` value with the Id of the MASTER account (the one who defined the organization)

/!\ This lambda will call itself asynchronously for each account of the organization

## Env Var :

API_RETRY_ATTEMPTS : mandatory, set it to "10" to indicate number of retry when calling any AWS api

EXCLUDE_ACCOUNTS : optional, list of account id or account name separated  by a `;` . A comment starting with # may be at the end of the line. It may be a good idea to excule the MASTER and the SECU account.

DRY_RUN : mandatory : set it to "True" to not start or stop instances, or "False" to effectively act on instances

## Tag Example 

Some example of the "openinghours" tag :
- `*:-*` : stop instance at every hour
- `*:8-20;Sat:-*;Sun:-*` : start instance every day at 8 and stop it at 20. On Sat and Sun, instance will be stopped every hour
- `Mon:8-;Fri:-20;TZ:Europe/Paris` : start instance on Monday at 8, stop it on Friday at 20, with Europe/Paris time zone
- `Mon:8-9;Mon:20-21;TZ:UTC` : start instance on monday from 8 to 9 and 20 to 21 UTC

# Set up the scheduling

- On the region on which you install the Lambda, create an Event Bridge event to trigger the Lambda at scheduled time.
- Plan the event to be triggered at every hour :
```
    Description: Every hour, call the Lambda function
    Event bus: default
    Schedule expression: cron(0 * * * ? *)
```