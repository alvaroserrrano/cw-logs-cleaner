import os
import logging
import click
from .delete_empty_log_streams import delete_empty_log_streams
from .set_log_retention import set_log_retention


@click.group()
@click.pass_context
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="not executing program, just showing a simulation",
)
@click.option("--region", help="aws region", required=False)
@click.option("--profile", help="aws profile", required=False)
def main(ctx, dry_run, region, profile):
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "WARN"))
    ctx.obj = ctx.params


@main.command(name="set-log-retention")
@click.pass_context
@click.option("--days", type=int, required=False, default=30, help="retention period")
@click.option("--overwrite", is_flag=True, default=False, help="existing retention periods")
def set_log_retention_command(ctx, days, overwrite):
    set_log_retention(ctx.obj["region"], ctx.obj["profile"], ctx.obj["dry_run"], overwrite, days)


@main.command(name="delete-empty-log-streams")
@click.pass_context
@click.option(
    "--prefix",
    type=str,
    required=False,
    help="of selected log group only",
)
@click.option(
    "--rm-non-empty",
    is_flag=True,
    default=False,
    help="remove all log streams from target log group",
)
def delete_empty_log_streams_command(ctx, prefix, rm_non_empty):
    delete_empty_log_streams(
        prefix,
        rm_non_empty,
        ctx.obj["dry_run"],
        ctx.obj["region"],
        ctx.obj["profile"],
    )


if __name__ == "__main__":
    main()