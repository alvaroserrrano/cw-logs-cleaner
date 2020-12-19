import boto3
from botocore.exceptions import ClientError
from .logger import log
import os

cw_logs = None
def set_log_retention(
  region: str = None,
  profile: str = None,
  dry_run: bool = False,
  overwrite: bool = False,
  days_to_retain: int = 30
):
  global cw_logs

  boto_session = boto3.Session(region_name=region, profile_name=profile)
  cw_logs = boto_session.client("logs")

  for page in cw_logs.get_paginator("describe_log_groups").paginate():
    for group in page["logGroups"]:
      group_name = group["logGroupName"]
      retention_period = group.get("retentionInDays")
      if not retention_period or (overwrite and int(retention_period) != days_to_retain):
        try:
          if retention_period:
            log.info("Overwriting %s retention period. New retention period is %s", group_name, days_to_retain)
          else:
            log.info("Setting %s default retention period to %s", group_name, days_to_retain)
          if dry_run:
            continue
          cw_logs.put_retention_policy(logGroupName=group_name, retentionInDays=days_to_retain)
        except ClientError as e:
          log.error(
            "Error setting default retention period of group %s to %s.\n Error: %s", group_name, days_to_retain, e
          )
      else:
        log.debug("retention period of %s was already set to %s", group_name, retention_period)

def handle(event, context):
  global cw_logs

  cw_logs = boto3.client("logs")

  # Error handling
  dry_run = event.get("dry_run", False)
  if "dry_run" in event and not isinstance(dry_run, bool):
    raise ValueError("dry_run must be a boolean param")
  
  overwrite = event.get("overwrite", False)
  if "overwrite" in event and not isinstance(overwrite, bool):
    raise ValueError("overwrite must be a boolean param")

  default_retention_in_days = int(os.getenv("DEFAULT_RETENTION_IN_DAYS", "30"))
  days = event.get('days', default_retention_in_days)
  if "days" in event and not isinstance(days, int):
    raise ValueError("Number of days to retain logs must be an int")

  set_log_retention(dry_run, overwrite, days)





  
  

