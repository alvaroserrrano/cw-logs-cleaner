import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from .logger import log
from datetime import datetime, timedelta

cw_logs = None

def ms_to_datetime(ms: int) -> datetime:
    return datetime(1970, 1, 1) + timedelta(milliseconds=ms)

def _delete_empty_log_streams(
  group: dict,
  rm_non_empty: bool = False,
  dry_run: bool = False
):
  now = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
  group_name = group["logGroupName"]
  retention_period = group.get("retentionInDays", 0)
  if not retention_period:
    log.info("Skip. %s has no retention period set", group_name)
    return
  log.info("deleting log streams older than %s days from %s", retention_period, group_name)
  kwargs = {
    "logGroupName": group_name,
    "orderBy": "LastEventTime",
    "descending": False,
    "PaginationConfig": {"PageSize": 50},
  }
  for page in cw_logs.get_paginator("describe_log_streams").paginate(**kwargs):
    for stream in page["logStreams"]:
      log_stream_name = stream["logStreamName"]
      last_event = ms_to_datetime(
          stream.get("lastEventTimestamp", stream.get("creationTime"))
      )
      if (
          last_event > (now - timedelta(days=retention_period))
          and "lastEventTimestamp" not in stream
      ):
        log.info("Keep %s, empty log stream %s, created on %s", group_name, log_stream_name, last_event)
        continue
      elif last_event > (now - timedelta(days=retention_period)):
        log.info("No log streams older than retention period were found in %s", group_name)
        return
      if not rm_non_empty:
        events = cw_logs.get_log_events(
          logGroupName=group_name,
          logStreamName=log_stream_name,
          startFromHead=False,
          limit=2,
        )
        if events["events"]:
          log.warn("Keeping log group %s because it is not empty. Last event found on %s", group_name, log_stream_name, last_event)
          continue
      log.info("deleting log stream %s from %s", log_stream_name, group_name)
      if dry_run:
        continue
      try:
        cw_logs.delete_log_stream(logGroupName=group_name, logStreamName=log_stream_name)
      except ClientError as e:
        log.error("error deleting log stream %s from %s. \n Error: %s", log_stream_name, group_name, e)

def delete_empty_log_streams(
  prefix: str = None,
  rm_non_empty: bool = False,
  dry_run: bool = False,
  region: str = None,
  profile: str = None,
):
  global cw_logs

  boto_session = boto3.Session(region_name=region, profile_name=profile)
  cw_logs = boto_session.client("logs", config=Config(retries=dict(max_attempts=10)))

  kwargs = {"PaginationConfig": {"PageSize": 50}}

  if prefix:
    kwargs["logGroupNamePrefix"] = prefix
    for page in cw_logs.get_paginator("describe_log_groups").paginate(**kwargs):
      for group in page["logGroups"]:
        _delete_empty_log_streams(group, rm_non_empty, dry_run)

def handle(event, context):
    global cw_logs

    cw_logs = boto3.client("logs", config=Config(retries=dict(max_attempts=10)))

    dry_run = event.get("dry_run", False)
    if "dry_run" in event and not isinstance(dry_run, bool):
        raise ValueError("dry_run param must be a bool")

    rm_non_empty = event.get("rm_non_empty", False)
    if "rm_non_empty" in event and not isinstance(rm_non_empty, bool):
        raise ValueError("rm_non_empty param must be a bool")

    prefix = event.get("prefix")
    if prefix:
        delete_empty_log_streams(prefix, rm_non_empty, dry_run)
