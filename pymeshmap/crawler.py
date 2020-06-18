"""Collect data from all the nodes in an AREDN network."""

import asyncio
import json
import re
import typing as t
from collections import defaultdict
from ipaddress import IPv4Address

import aiohttp
from loguru import logger

from . import models, parser

# TODO: loguru has an async option, does it make a difference here?


async def map_network(host_name: str):
    """Map the AREDN mesh network."""

    # FIXME add semaphore to cap tasks
    tasks: t.List[t.Awaitable] = []
    async with aiohttp.ClientSession() as session:
        async for node_address in get_nodes(host_name):
            logger.debug("Creating task to poll {}", node_address)
            task = asyncio.create_task(poll_node(session, node_address))
            tasks.append(task)

        node_details = await asyncio.gather(*tasks, return_exceptions=True)

    for node in node_details:
        if isinstance(node, Exception):
            print(repr(node))
            continue
        print(node.info)
        if node.error:
            with open(f"{node.ip_address}.json", "w") as f:
                json.dump(node.json_data, f, indent=2)

    return


async def get_nodes(host_name: str) -> t.AsyncIterator[IPv4Address]:
    """Yield the IP addresses of nodes in the network.

    Rather than crawling the whole network and looking for each node's neighbors we
    query the list from OLSR.

    Based on `wxc_netcat()` in MeshMap the only lines we are interested in (when get the
    node list) are the ones that look (generally) like this (sometimes the second
    address is a CIDR address):

        "10.32.66.190" -> "10.80.213.95"[label="1.000"];

    """
    count = defaultdict(int)
    # node could show up multiple times so save the ones we've seen
    nodes_returned = set()
    node_regex = re.compile(r"^\"(\d{2}\.\d{1,3}\.\d{1,3}\.\d{1,3})\" -> \"\d+")

    # this can raise subclasses of OSError
    reader, writer = await asyncio.open_connection(host_name, 2004)
    while True:
        line_bytes = await reader.readline()
        if not line_bytes:
            break
        count["lines processed"] += 1
        line = line_bytes.decode("utf-8").strip()

        match = node_regex.match(line)
        if not match:
            count["lines skipped"] += 1
            continue
        logger.debug(line)
        node_address = match.group(1)
        if node_address in nodes_returned:
            count["duplicate node"] += 1
            continue
        nodes_returned.add(node_address)
        count["nodes returned"] += 1
        yield IPv4Address(node_address)

    writer.close()

    logger.info("OLSR Statistics: {}", dict(count))
    await writer.wait_closed()

    return


class NodeResult(t.NamedTuple):
    ip_address: IPv4Address
    info: t.Optional[t.Any]  # FIXME: this should be a data class
    error: t.Optional[t.Any]  # FIXME: this should be an error
    json_data: t.Optional[t.Dict]


async def poll_node(
    session: aiohttp.ClientSession, node_address: IPv4Address, *, options: t.Dict = None
) -> NodeResult:
    """Query a node to get the parsed information.

    This calls some synchronous code for processing the JSON response.  Testing will
    determine whether this is an issue.

    Args:
        session: aiohttp session object (docs recommend to pass around single object)
        node_address: IP address of the node to query
        options: Dictionary of additional querystring options to pass to `sysinfo.json`

    Returns:

    """

    logger.debug("{} begin polling...", node_address)

    params = {"services_local": 1}
    if options:
        params.update(options)

    error = None

    # FIXME: add more error handling
    async with session.get(
        f"http://{node_address}:8080/cgi-bin/sysinfo.json", params=params
    ) as resp:
        json_data = await resp.json()

    node_info = parser.load_node_data(json_data)

    if node_info is None:
        # FIXME: this should be an enum
        error = "Failed to parse"

    return NodeResult(node_address, node_info, error, json_data)
