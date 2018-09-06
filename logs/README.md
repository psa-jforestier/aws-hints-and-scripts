Script to work with AWS CloudWatch Logs service.

- `printlog.py` : get logs from CloudWatch log, view it in follow mode (like tail -f). Code ased on https://alexwlchan.net/2017/11/fetching-cloudwatch-logs/

Example :

`python printlog.py //myloggroup my/log/stream --start 2018-09-05T00:00:00.000 --end 2018-09-06T00:00:00.000` : retreive all logs of a group and stream from date to date.

`python printlog.py /myloggroup apache/access -f` : follow this log stream (use ^C to quit)
