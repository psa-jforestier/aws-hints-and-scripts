#!/bin/bash

function usage() {
        cat << EOF
cw-annotation.sh -d DASHBOARDNAME -w WIDGETNAME -t LABEL
Add annotations to an existing Cloudwatch dashboard.
Parameters :
-d DASHBOARDNAME the name of the dashboard
-w WIDGETNAME the name of the widget where the annotation will be added
-l LABEL label of the annotation
-v VALUE value of the date of annotation (default : current time, format ISO_8601)
-c COLOR six-digit HTML hex color (default : next available color)
-r REGION aws region (default : AWS_DEFAULT_REGION)
EOF

}

AWS_REGION=$AWS_DEFAULT_REGION
while getopts ":d:w:l:v:c:f:r:" arg; do
        case $arg in
		d) DASHBOARDNAME=$OPTARG;;
		w) WIDGETNAME=$OPTARG;;
		l) LABEL=$OPTARG;;
		v) VALUE=$OPTARG;;
		c) COLOR=$OPTARG;;
		f) FILL=$OPTARG;;
		r) AWS_REGION=$OPTARG;;
                ?) usage
                        exit 2;;
        esac
done

if [[ "$DASHBOARDNAME" == "" ]]; then
	echo "ERROR : you must indicate a dasboard name (-d DASHBOARDNAME)"
	echo "Use the following command to get all the dashboards :"
	echo " aws cloudwatch list-dashboards --output table"
	exit 1
fi

if [[ "$WIDGETNAME" == "" ]]; then
	echo "ERROR : you must indicate a widget name (-w WIDGETNAME)"
	echo "Use the following command to get all the widgets of the dashboard $DASHBOARDNAME :"
	echo " aws cloudwatch get-dashboard --dashboard-name $DASHBOARDNAME | jq '.DashboardBody | fromjson | .widgets[].properties.title'"
	exit 1
fi

if [[ "$LABEL" == "" ]]; then
	echo "ERROR : you must indicate a label for the annotation (-l LABEL)"
	exit 1
fi


tmp="$(mktemp /tmp/cw-annotation.XXXXXXXXX)"
#tmp=/tmp/cw.tmp

echo "Getting dashboard $DASHBOARDNAME"
aws cloudwatch get-dashboard --region $AWS_REGION --dashboard-name $DASHBOARDNAME | jq '.DashboardBody | fromjson' >$tmp

echo "Creating the new dashboard"
if [[ "$VALUE" == "" ]]; then
	VALUE=$(date --iso-8601=sec)
	VALUE=$(date +"%FT%T.000Z")
fi

# there is a trick here with the "color" attribute : the value must not be empty. If no color is
# needed, we must not have the attribute at all.
if [[ "$COLOR" == "" ]]; then
	cat $tmp | jq --arg VALUE "$VALUE" --arg LABEL "$LABEL"                      --arg TITLE "$WIDGETNAME" '(.widgets[] | select(.properties.title==$TITLE)).properties.annotations.vertical += [{"label":$LABEL, "value":$VALUE}]' > ${tmp}.new
else
	cat $tmp | jq --arg VALUE "$VALUE" --arg LABEL "$LABEL" --arg COLOR "$COLOR" --arg TITLE "$WIDGETNAME" '(.widgets[] | select(.properties.title==$TITLE)).properties.annotations.vertical += [{"label":$LABEL, "value":$VALUE, "color":$COLOR}]' > ${tmp}.new
fi


aws cloudwatch put-dashboard --region $AWS_REGION --dashboard-name $DASHBOARDNAME --dashboard-body file://${tmp}.new 

rm -f ${tmp} ${tmp}.new
