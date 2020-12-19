# AWS Cloudwatch Log Utils

- Set default retention period on default log groups.
- Remove empty log streams after the retention period has finished (AWS does not do this automatically).

Setuptools implementation for better integration with Click library

## run as a CLI program

```
make
pip install git+https://github.com/medlabmg/aws-mmg-cw-logs.git
```

## global params

- Simulates program execution
  `--dry-run`

## set default retention to 30 days

Allowed params:

- --days -> Specify number of days to retaing logs
- --overwrite -> Overwrites the retention-period of existing log streams

### Example

`aws-mmg-cw-logs set-log-retention --days 30`

## delete empty log streams

Allowed params:

- --log-group-name -> Name of the log group whose empty log streams you want to delete
- --rm-non-empty -> to delete all log streams from the target log group

### Example

`aws-mmg-cw-logs delete-empty-log-streams`

## aws cloud deployment

```sh
git clone https://github.com/alvaroserrrano/aws-mmg-cw-logs.git
cd aws-mmg-cw-logs
aws cloudformation deploy \
	--capabilities CAPABILITY_IAM \
	--stack-name aws-mmg-cw-logs \
	--template-file ./cloudformation/aws-mmg-cw-logs.yaml \
	--parameter-overrides LogRetentionInDays=30
```

This will install the log minder in your AWS account and run every hour.

## region and profile selection

AWS regions and credential profiles can be selected via command line
arguments or environment variables.

## To be Done

Upload to ECR
