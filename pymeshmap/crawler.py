"""Collect data from all the nodes in an AREDN network."""

import asyncio
import typing as t

import aiohttp
import click
from loguru import Logger, logger

from . import models, parser

# TODO: loguru has an async option, does it make a difference here?


@click.command("map-network")
@click.option(
    "--noupdate", "-N", "no_update", is_flag=True, help="Do not update database"
)
@click.option("--verbose", "-v", is_flag=True, help="Output more details")
@click.pass_obj
def main(config, no_update, verbose):
    """CLI sub-command entry point for mapping the network."""

    # verify no other mapping process is running

    # mark the mapping has begun (and commit!)

    # get list of nodes to query

    # process list of nodes via async
    # FIXME: where we start asyncio will likely change if this is running cron or not
    node_info = asyncio.run(query_nodes(node_list))

    # (typically) update database

    # *always* clear the "running" flag

    # (possibly) update link data

    return


async def query_nodes(nodes: t.List):
    """Main entry point for the asyncio version of the crawler."""

    # FIXME: this is just a stub

    tasks: t.List[t.Awaitable] = []
    async with aiohttp.ClientSession() as session:
        for node in nodes:
            node_logger = logger.bind(node=node)
            node_logger.info("Creating polling task")
            tasks.append(poll_node(session, node, log=node_logger))

    return await asyncio.gather(*tasks, return_exceptions=True)


async def poll_node(
    session: aiohttp.ClientSession, node: str, *, log: Logger, options: t.Dict = None
) -> t.Union[models.NodeInfo, models.IgnoreHost]:
    """Query a node to get the parsed information.

    This calls some synchronous code for processing the JSON response.  Testing will
    determine whether this is an issue.

    Args:
        session: aiohttp session object (docs recommend to pass around single object)
        node: Name or IP address of the node to query (should be IP?)
        log: Loguru logging object
        options: Dictionary of additional querystring options to pass to `sysinfo.json`

    Returns:
        Database model either representing the node or to ignore it

    """

    # FIXME: this is just a stub

    log.debug("Begin polling...")

    params = {"services_local": 1}
    if options:
        params.update(options)

    async with session.get(
        f"http://{node}:8080/cgi-bin/sysinfo.json", params=params
    ) as resp:
        node_data = await resp.json()

    node_info = parser.load_node_data(node_data, log=log)

    # print node if running verbose

    if node_info is None:
        # failed to parse, create a IgnoreHost record?
        return
