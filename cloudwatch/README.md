# Some Cloudwatch helpers and scripts

## cw-annotations.sh

Add vertical, or horizontal annotations (or labels) to an existing Cloudwatch dashboard. Use the `aws cloudwatch` CLI commands to get the Dashboard ID, and create the new vertical label. This script use `jq` (https://stedolan.github.io/jq/), and need to have write access to `/tmp/`.
