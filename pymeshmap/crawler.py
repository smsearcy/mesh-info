"""Collect data from all the nodes in an AREDN network."""

import asyncio
import enum
import json
import re
import time
import typing as t
from collections import defaultdict
from ipaddress import IPv4Address

import aiohttp
from loguru import logger

from . import models, parser

# TODO: make this a configuration variable
HTTP_CONNECTION_TIMEOUT = 30


class NodeError(enum.Enum):
    INVALID_RESPONSE = enum.auto()
    PARSE_ERROR = enum.auto()
    CONNECTION_ERROR = enum.auto()


async def map_network(host_name: str):
    """Map the AREDN mesh network."""

    start_time = time.perf_counter()

    # TODO: add semaphore to cap tasks?  (will require passing to `poll_node()`)
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

    for node in node_details:
        if isinstance(node, Exception):
            print(repr(node))
            continue
        print(node.info)
        if node.error:
            print(f"Saving results for {node.ip_address} due to an error...")
            with open(f"sysinfo-{node.ip_address}.json", "w") as f:
                f.write(node.raw_response)

    crawler_finished = time.perf_counter()

    print(f"Querying nodes took {crawler_finished - start_time:.2f} seconds")

    return


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
    reader, writer = await asyncio.open_connection(host_name, port)
    while True:
        line_bytes = await reader.readline()
        if not line_bytes:
            break
        yield line_bytes.decode("utf-8").rstrip()

    writer.close()
    await writer.wait_closed()


async def get_nodes(
    olsr_records: t.AsyncIterable[str], *, ignore_hosts: t.Set[str] = None
) -> t.AsyncIterator[IPv4Address]:
    """Process OLSR records, yielding the IP addresses of nodes in the network.

    Based on `wxc_netcat()` in MeshMap the only lines we are interested in (when get the
    node list) are the ones that look (generally) like this (sometimes the second
    address is a CIDR address):

        "10.32.66.190" -> "10.80.213.95"[label="1.000"];

    """
    ignore_hosts = ignore_hosts or set()
    count = defaultdict(int)
    # node could show up multiple times so save the ones we've seen
    nodes_returned = set()
    node_regex = re.compile(r"^\"(\d{2}\.\d{1,3}\.\d{1,3}\.\d{1,3})\" -> \"\d+")

    async for line in olsr_records:
        count["lines processed"] += 1

        match = node_regex.match(line)
        if not match:
            count["lines skipped"] += 1
            continue
        logger.debug(line)
        node_address = match.group(1)
        if node_address in ignore_hosts:
            count["ignored node"] += 1
            continue
        if node_address in nodes_returned:
            count["duplicate node"] += 1
            continue
        nodes_returned.add(node_address)
        count["nodes returned"] += 1
        yield IPv4Address(node_address)

    logger.info("OLSR Statistics: {}", dict(count))

    return


class NodeResult(t.NamedTuple):
    ip_address: IPv4Address
    info: t.Optional[parser.SystemInfo]
    error: t.Optional[NodeError]
    raw_response: t.Optional[str]


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
