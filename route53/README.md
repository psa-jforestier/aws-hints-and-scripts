## r53update.sh
Script to update a Route 53 DNS record with the public hostname of the running EC2 instance.

Usage :
```
r53update.sh <options>
Options:
-name <dns record>  DNS record to update
-name-from-tag <tag> DNS record will come from the <tag> value of the EC2
-ttl <value>        TTL to update (default : 60s)
-profile <aws cli profile>
```


This command can be include at boot to update automatically the DNS record :
- Use "user data" settings of EC2 : add `#cloud-boothook` before shebang on the user data area, or the script will be fired only the first boot (and not on reboot). Also, be sure to have sufficient credentials to execute AWS CLI command.
```
#cloud-boothook
#!/bin/bash
yum update -y --security --bugfix
su - ec2-user -c "/home/ec2-user/cloudscripts/aws/scripts/route53/r53update.sh -name-from-tag Name -ttl 60" > /tmp/r53update.log 2> /tmp/r53update.err
```
- This script use the default AWS CLI credentials, or the following IAM role :
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "route53:ListHostedZones",
                "route53:ChangeResourceRecordSets"
            ],
            "Resource": "*"
        }
    ]
}
```
- Add the role "`ec2:DescribeTags`" if you use the `-name-from-tag` option.
