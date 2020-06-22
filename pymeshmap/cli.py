"""Main command-line entry point for `pymeshmap`."""

import asyncio
import sys

import click
from loguru import logger

from pymeshmap import crawler

# TODO: replace these with proper configuration
LOCAL_NODE_NAME = "localnode.local.mesh"


@click.group()
@click.pass_context
def main(ctx):
    # TODO: configure environment
    ctx.obj = None
    return


@main.command()
@click.option("--no-update", is_flag=True)
@click.option("--verbose", is_flag=True)
@click.option("--service", is_flag=True)
@click.pass_obj
def map_network(config, no_update, verbose, service):
    """"""

    if service:
        raise NotImplementedError("Not implemented yet")

    try:
        asyncio.run(crawler.map_network(LOCAL_NODE_NAME), debug=True)
    except OSError as e:
        raise click.ClickException(f"{e!s}") from e
