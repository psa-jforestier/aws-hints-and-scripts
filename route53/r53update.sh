#!/bin/bash
function print_help()
{
echo "r53update
Use to set dynamically a Route53 DNS record to the public hostname of the running instance.

usage: r53update <options>
Options:
-name <dns record>  DNS record to update
-name-from-tag <tag> DNS record will come from the <tag> value of the EC2
-ttl <value>        TTL to update (default : 60s)
-profile <aws cli profile>

example :
r53update -name myhostname.project.domain.com -ttl 300

This script use differents technics to get the public hostname of the running instance :
- call program \"ec2-metadata -p\"
- if failed, use \"http://instance-data/latest/meta-data/public-hostname\"
- if failed, use \"http://169.254.169.254/latest/meta-data/public-hostname\"
- if failed, use \"http://169.254.169.254/latest/meta-data/public-ipv4\" and a A record will be set
- if failed, do not update record.

The command fail if the record can't be update (typically, the instance do not have sufficient role, 
or there is no credentials available).

To start this script at boot add (as root) :
su - ec2-user -c \"/home/ec2-user/r53update.sh -name loadtest.configv3.awsmpsa.com -ttl 300\"

Warning : if using EC2 User Data , you must add in the User Data text area
#cloud-boothook
before
#!/bin/sh
or the user data scripts will not be executed

The IAM role executing this script must have the following ressource policy :
  route53:ListHostedZones
  route53:ChangeResourceRecordSets
  ec2:DescribeTags
"
}

function strindex() { 
  x="${1%%$2*}"
  [[ "$x" = "$1" ]] && echo -1 || echo "${#x}"
}

#command called in default mode
if [ "$#" -eq 0 ]; then
        print_help
	exit 0
fi

DNSNAME=""
DNSTTL=60
TAG=""
CURLOPT="--fail --max-time 1"

#start processing command line arguments
while [ "$1" != "" ]; do
        case $1 in
	-h | --help)
		print_help
		exit 0
		;;
	-name)
		DNSNAME=$2
		shift
		;;
	-name-from-tag)
		TAG=$2
		shift
		;;
	-ttl)
		DNSTTL=$2
		shift
		;;
	-profile)
		AWS_PROFILE=$2
		shift
		;;
	esac
	shift
done

if [[ "$TAG" != "" ]]; then
	#// Read the dns name from the EC2 TAGs list
	echo "Search for DNS name in tag \"$TAG\""
	MY_INSTANCEID=$(curl -s $CURLOPT http://instance-data/latest/meta-data/instance-id || curl -s $CURLOPT http://169.254.169.254/latest/meta-data/instance-id)
	echo "  The instance_id is $MY_INSTANCEID"
	export AVAILABILITY_ZONE=`wget -qO- http://instance-data/latest/meta-data/placement/availability-zone`
	export REGION_ID=${AVAILABILITY_ZONE:0:${#AVAILABILITY_ZONE} - 1}
	echo "  The region is $REGION_ID"
	CMD=$(aws ec2 describe-tags --region $REGION_ID --filters "Name=resource-id,Values=$MY_INSTANCEID" --query "Tags[?Key=='$TAG'].Value" --output text)
	DNSNAME=($CMD)
	echo "  The DNS name associated to this tag is $DNSNAME"
fi

if [ "$DNSNAME" == "" ]; then
	echo "Error : missing -name <dns record> parameters" >&2
	exit 1
fi

DNSRECORDNAME="${DNSNAME}."

echo "Update record of $DNSRECORDNAME"

zid=( $(aws route53 list-hosted-zones --query 'HostedZones[*].{Id:Id,Name:Name}' --output text))
if [ "$?" != 0 ]; then
	echo "!! Unable to query Route53 api" >&2
	exit 1
fi
i=0
CHOOSEN_ZONEID=""
CHOOSEN_ZONENAME=""
MIN_POS=999
while [ true ]; do
	zoneid=${zid[$i]}
	if [ "$zoneid" == "" ]; then
		break
	fi
	let "i++"
	zonename=${zid[$i]}
	let "i++"
	echo "Found zone $zoneid $zonename"
	pos=$(strindex "$DNSRECORDNAME" "$zonename")
	if [ "$pos" -gt 0 ]; then
		if [ "$pos" -lt "$MIN_POS" ]; then
			MIN_POS=$pos
			CHOOSEN_ZONEID=$zoneid
			CHOOSEN_ZONENAME=$zonename
		fi
	fi
done
if [ "$CHOOSEN_ZONENAME" == "" ]; then
	echo "!! Unable to find a hosted zone for $DNSRECORDNAME" >&2
	exit 4
fi
echo "Work with zone $CHOOSEN_ZONENAME"

MY_PUBLIC_HOSTNAME=$(ec2-metadata -p | cut -d " " -f 2)
DNSTYPE="CNAME"
if [ "$MY_PUBLIC_HOSTNAME" == "" ]; then
	MY_PUBLIC_HOSTNAME=$(curl $CURLOPT http://instance-data/latest/meta-data/public-hostname || curl $CURLOPT http://169.254.169.254/latest/meta-data/public-hostname)
	if [ "$MY_PUBLIC_HOSTNAME" == "" ]; then
		DNSTYPE="A"
		MY_PUBLIC_HOSTNAME=$(curl $CURLOPT http://169.254.169.254/latest/meta-data/public-ipv4)
		if [ "$MY_PUBLIC_HOSTNAME" == "" ]; then
			echo "!! Unable to get public hostname" >&2
			exit 2
		fi
	fi
fi

echo "Public DNS record $DNSTYPE : $MY_PUBLIC_HOSTNAME"

echo "Now updating DNS record \"$DNSRECORDNAME\" of zone ID $CHOOSEN_ZONEID ($CHOOSEN_ZONENAME) with TLL $DNSTTL, record type $DNSTYPE and value $MY_PUBLIC_HOSTNAME"
aws route53 change-resource-record-sets --hosted-zone-id $CHOOSEN_ZONEID --change-batch \
	"{\"Comment\": \"Updated with r53update script\",\"Changes\": [{\"Action\": \"UPSERT\",\"ResourceRecordSet\": {\"Name\":\"$DNSRECORDNAME\",\"TTL\":$DNSTTL,\"Type\":\"$DNSTYPE\",\"ResourceRecords\": [{\"Value\":\"$MY_PUBLIC_HOSTNAME\"}]}}]}" \
	--output table
if [ "$?" != "0" ]; then
	echo "!! Unable change Route53 DNS record" >&2
	exit 5
fi
