## r53update.sh
Script to update a Route 53 DNS record with the public hostname of the running EC2 instance.

Usage :
`r53update.sh -name subdomain.example.com [-ttl 60]`
This command can be include at boot to update automatically the DNS record :
- Use "user data" settings of EC2 : add `#cloud-boothook` before shebang on the user data area, or the script will be fired only the first boot (and not on reboot). Also, be sure to have sufficient credentials to execute AWS CLI command.


