"""Collect data from all the nodes in an AREDN network."""

from __future__ import annotations

import asyncio
import enum
import json
import re
import time
import typing as t
from collections import defaultdict

import aiohttp
from loguru import logger

from . import parser

# TODO: make this a configuration variable
HTTP_CONNECTION_TIMEOUT = 30


class NodeError(enum.Enum):
    INVALID_RESPONSE = enum.auto()
    PARSE_ERROR = enum.auto()
    CONNECTION_ERROR = enum.auto()


class NodeResult(t.NamedTuple):
    ip_address: str
    info: t.Optional[parser.SystemInfo]
    error: t.Optional[NodeError]
    raw_response: t.Optional[str]


async def network_nodes(
    host_name: str, *, save_errors: bool = False
) -> t.List[parser.SystemInfo]:
    """Get information for all the active nodes on the network."""

    start_time = time.monotonic()

    tasks: t.List[t.Awaitable] = []
    timeout = aiohttp.ClientTimeout(total=HTTP_CONNECTION_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        olsr_records = _query_olsr(host_name)
        async for node_address in get_nodes(olsr_records):
            logger.debug("Creating task to poll {}", node_address)
            task = asyncio.create_task(poll_node(session, node_address))
            tasks.append(task)

        node_details: t.List[NodeResult] = await asyncio.gather(
            *tasks, return_exceptions=True
        )

    crawler_finished = time.monotonic()
    logger.info(f"Querying nodes took {crawler_finished - start_time:.2f} seconds")

    nodes = []
    count: t.DefaultDict[str, int] = defaultdict(int)
    for node in node_details:
        count["total"] += 1
        if isinstance(node, Exception):
            # this shouldn't happen but just in case
            count["exceptions"] += 1
            logger.error("Unhandled exception polling node: {}", node)
            continue
        if node.error:
            # this error would have already been logged
            count["errors (total)"] += 1
            count[f"errors ({node.error!s})"] += 1
            if save_errors and node.raw_response:
                logger.info(f"Saving results for {node.ip_address} due to an error...")
                with open(f"{node.ip_address}-response.txt", "w") as f:
                    f.write(node.raw_response)
            continue
        if not node.info:
            count["missing data"] += 1
            logger.warning("Node information for {} missing", node.ip_address)
            continue
        count["successes"] += 1
        nodes.append(node.info)

    return nodes


async def _query_olsr(host_name: str, port: int = 2004) -> t.AsyncIterator[str]:
    """Yield lines from OLSR routing daemon.

    This was separated into its own function both for testing purposes and because it
    is used by several different processes because the local OLSR daemon has a lot
    of information about the mesh network.

    Args:
        host_name: Name of host to connect to
        port: Port to connect to

    Yields:
        Each line in the OLSR output, converted to UTF-8 and trailing newline removed

    """
    # this can raise subclasses of OSError
    try:
        reader, writer = await asyncio.open_connection(host_name, port)
    except OSError as e:
        logger.error("Failed to connect to {}:{} ({!s})", host_name, port, e)
        return

    while True:
        line_bytes = await reader.readline()
        if not line_bytes:
            break
        yield line_bytes.decode("utf-8").rstrip()

    writer.close()
    await writer.wait_closed()


async def get_nodes(
    olsr_records: t.AsyncIterable[str], *, ignore_hosts: t.Set[str] = None
) -> t.AsyncIterator[str]:
    """Process OLSR records, yielding the IP addresses of nodes in the network.

    Based on `wxc_netcat()` in MeshMap the only lines we are interested in (when get the
    node list) are the ones that look (generally) like this (sometimes the second
    address is a CIDR address):

        "10.32.66.190" -> "10.80.213.95"[label="1.000"];

    """
    ignore_hosts = ignore_hosts or set()
    count: t.DefaultDict[str, int] = defaultdict(int)
    # node could show up multiple times so save the ones we've seen
    nodes_returned = set()
    node_regex = re.compile(r"^\"(\d{2}\.\d{1,3}\.\d{1,3}\.\d{1,3})\" -> \"\d+")

    async for line in olsr_records:
        count["lines processed"] += 1

        match = node_regex.match(line)
        if not match:
            count["lines skipped"] += 1
            continue
        logger.trace(line)
        node_address = match.group(1)
        if node_address in ignore_hosts:
            count["ignored node"] += 1
            continue
        if node_address in nodes_returned:
            count["duplicate node"] += 1
            continue
        nodes_returned.add(node_address)
        count["nodes returned"] += 1
        yield node_address

    logger.info("OLSR Statistics: {}", dict(count))

    return


async def poll_node(
    session: aiohttp.ClientSession, node_address: str, *, options: t.Dict = None
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

    try:
        async with session.get(
            f"http://{node_address}:8080/cgi-bin/sysinfo.json", params=params
        ) as resp:
            # status = resp.status
            response_text = await resp.text()
    except aiohttp.ClientError as e:
        logger.error("{}: Connection issue: {}", node_address, e)
        return NodeResult(node_address, None, NodeError.CONNECTION_ERROR, str(e))

    try:
        json_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error("{}: Invalid JSON response: {}", node_address, e)
        return NodeResult(node_address, None, NodeError.INVALID_RESPONSE, response_text)

    node_info = parser.load_node_data(json_data)

    if node_info is None:
        return NodeResult(node_address, None, NodeError.PARSE_ERROR, response_text)

    return NodeResult(node_address, node_info, None, response_text)
