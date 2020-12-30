"""Main module for getting information from nodes on an AREDN mesh network.

Provides `asyncio` functions for crawling the network and polling the nodes.
Defines data classes for modeling the network information independent of the database
models because there might be parsed values that are not ready to be stored yet.

Throughout this module there are references to OLSR (Optimized Link State Routing)
but what is really meant is the OLSR daemon that runs on wireless node in the mesh.

"""

from __future__ import annotations

import asyncio
import enum
import json
import re
import time
from collections import defaultdict
from typing import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    DefaultDict,
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

import aiohttp
import attr
from loguru import logger

from .aredn import SystemInfo, load_system_info


@attr.s(auto_attribs=True)
class Poller:
    """Class to handle polling the network nodes and links.

    Mainly this is so we can initialize it with the configuration settings and then
    call them later.

    """

    local_node: str = "localnode.local.mesh"
    max_connections: int = 50
    connect_timeout: int = 20
    read_timeout: int = 20
    total_timeout: Optional[int] = None
    # if we add ignored_nodes it should be here

    async def network_info(self) -> NetworkInfo:
        """Helper function to query node and link information asynchronously.

        Returns:
            Named tuple with a list of all the nodes successfully queried,
            a list of the links on the network,
            and a dictionary of errors keyed by the IP address.

        """

        node_task = asyncio.create_task(self.network_nodes())
        # without a 1 second sleep here only one task was able to get data from OLSR
        # (but I'm on a small network)
        # if only one task can access that daemon at once then these will need to happen
        # sequentially (fortunately the links process is super fast)
        await asyncio.sleep(1)
        link_task = asyncio.create_task(self.network_links())

        nodes: NetworkNodes = await node_task
        links: List[LinkInfo] = await link_task

        return NetworkInfo(nodes.nodes, links, nodes.errors)

    async def network_nodes(self) -> NetworkNodes:
        """Asynchronously gets information for all the nodes on the network.

        Getting a list of the nodes is done via connecting to the OLSR

        Returns:
            Named tuple with a list of all the nodes successfully queried and
            a dictionary of errors keyed by the IP address.

        """
        start_time = time.monotonic()

        tasks: List[Awaitable] = []
        connector = aiohttp.TCPConnector(limit=self.max_connections)
        timeout = aiohttp.ClientTimeout(
            total=self.total_timeout,
            sock_connect=self.connect_timeout,
            sock_read=self.read_timeout,
        )
        async with aiohttp.ClientSession(
            timeout=timeout, connector=connector
        ) as session:
            olsr_records = _query_olsr(self.local_node)
            async for node_address in _get_node_addresses(olsr_records):
                logger.debug("Creating task to poll {}", node_address)
                task = asyncio.create_task(poll_node(session, node_address))
                tasks.append(task)

            # collect all the results in a single list
            node_details: List[NodeResult] = await asyncio.gather(
                *tasks, return_exceptions=True
            )

        crawler_finished = time.monotonic()
        logger.info("Querying nodes took {:.2f} seconds", crawler_finished - start_time)

        nodes = []
        errors = {}
        count: DefaultDict[str, int] = defaultdict(int)
        for node in node_details:
            count["total"] += 1
            if isinstance(node, Exception):
                # this shouldn't happen but just in case
                count["exceptions"] += 1
                logger.error("Unhandled exception polling a node: {!r}", node)
                continue
            if isinstance(node.result, NodeError):
                # this error would have already been logged
                count["errors (total)"] += 1
                count[f"errors ({node.result!s})"] += 1
                errors[node.ip_address] = (node.result, node.raw_response)
                continue
            count["successes"] += 1
            nodes.append(node.result)

        logger.info("Network nodes summary: {}", dict(count))
        return NetworkNodes(nodes, errors)

    async def network_links(self) -> List[LinkInfo]:
        """Asynchronously gets information about all links between nodes in the network.

        This is rather simple because all that information is available
        from the OLSR daemon running on the local node.
        Since this function does not need to crawl the network
        there is less need to be asynchronous
        but this way we can re-use a single OLSR query function

        Returns:
            List of `LinkInfo` data classes for each unique link in the network.

        """

        olsr_records = _query_olsr(self.local_node)
        links = [link async for link in _get_node_links(olsr_records)]
        logger.info("Network link count: {}", len(links))
        return links


class NetworkInfo(NamedTuple):
    """Combined results of querying the nodes and links on the network."""

    nodes: List[SystemInfo]
    links: List[LinkInfo]
    errors: Dict[str, Tuple[NodeError, str]]


class NetworkNodes(NamedTuple):
    """Results of querying the nodes on the network."""

    nodes: List[SystemInfo]
    errors: Dict[str, Tuple[NodeError, str]]


class NodeError(enum.Enum):
    """Enumerates possible errors when polling a node."""

    INVALID_RESPONSE = enum.auto()
    PARSE_ERROR = enum.auto()
    CONNECTION_ERROR = enum.auto()
    HTTP_ERROR = enum.auto()
    TIMEOUT_ERROR = enum.auto()

    def __str__(self):
        if "HTTP" in self.name:
            # keep the acronym all uppercase
            return "HTTP Error"
        return self.name.replace("_", " ").title()


class NodeResult(NamedTuple):
    """Results from polling a single node."""

    ip_address: str
    result: Union[SystemInfo, NodeError]
    raw_response: str


@attr.s(slots=True, auto_attribs=True)
class LinkInfo:
    """OLSR link information measuring the cost between nodes."""

    source: str
    destination: str
    cost: float

    @classmethod
    def from_strings(cls, source: str, destination: str, label: str) -> LinkInfo:
        cost = 99.99 if label == "INFINITE" else float(label)
        return cls(source, destination, cost)

    def __str__(self):
        return f"{self.source} -> {self.destination} ({self.cost})"


async def _query_olsr(host_name: str, port: int = 2004) -> AsyncIterator[str]:
    """Asynchronously yield lines from OLSR routing daemon.

    This was separated into its own function both for testing purposes and because it
    is used by several different processes because the local OLSR daemon has a lot
    of information about the mesh network.

    Args:
        host_name: Name of host to connect to
        port: Port to connect to

    Yields:
        Each line in the OLSR output, converted to UTF-8 and trailing newline removed

    """
    logger.trace("Connecting to OLSR daemon {}:{}", host_name, port)
    try:
        reader, writer = await asyncio.open_connection(host_name, port)
    except OSError as e:
        # Connection errors subclass `OSError`
        logger.error("Failed to connect to {}:{} ({!s})", host_name, port, e)
        return

    while True:
        line_bytes = await reader.readline()
        if not line_bytes:
            break
        yield line_bytes.decode("utf-8").rstrip()

    writer.close()
    await writer.wait_closed()


async def _get_node_addresses(olsr_records: AsyncIterable[str]) -> AsyncIterator[str]:
    """Process OLSR records, yielding the IP addresses of nodes in the network.

    Based on `wxc_netcat()` in MeshMap the only lines we are interested in
    (when getting the node list)
    are the ones that look (generally) like this
    (sometimes the second address is a CIDR address):

        "10.32.66.190" -> "10.80.213.95"[label="1.000"];

    """
    count: DefaultDict[str, int] = defaultdict(int)
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
        if node_address in nodes_returned:
            count["duplicate node"] += 1
            continue
        nodes_returned.add(node_address)
        count["nodes returned"] += 1
        yield node_address

    logger.info("OLSR Node Statistics: {}", dict(count))
    if count["nodes returned"] == 0:
        logger.warning(
            "Failed to find any nodes in {:,d} lines of OLSR data.",
            count["lines processed"],
        )

    return


async def poll_node(session: aiohttp.ClientSession, node_address: str) -> NodeResult:
    """Query a node via HTTP to get the information about that node.

    Args:
        session: aiohttp session object (docs recommend to pass around single object)
        node_address: IP address of the node to query

    Returns:
        Named tuple with the IP address,
        result of either `SystemInfo` or `NodeError`,
        and the raw response string.

    """

    logger.debug("{} begin polling...", node_address)

    params = {"services_local": 1}

    try:
        async with session.get(
            f"http://{node_address}:8080/cgi-bin/sysinfo.json", params=params
        ) as resp:
            status = resp.status
            response = await resp.read()
            # copy and pasting Unicode seems to create an invalid description
            # example we had was b"\xb0" for a degree symbol
            response_text = response.decode("utf-8", "replace")
    except asyncio.TimeoutError as e:
        # catch this first, because some exceptions use multiple inheritance
        logger.error("{}: {}", node_address, e)
        return NodeResult(node_address, NodeError.TIMEOUT_ERROR, "Timeout error")
    except aiohttp.ClientError as e:
        logger.error("{}: {}", node_address, e)
        return NodeResult(node_address, NodeError.CONNECTION_ERROR, str(e))
    except Exception as e:
        logger.error("{}: Unknown error connecting: {!r}", node_address, e)
        return NodeResult(node_address, NodeError.CONNECTION_ERROR, str(e))

    if status != 200:
        message = f"{status}: {response_text}"
        logger.error("{}: HTTP error {}", node_address, message)
        return NodeResult(node_address, NodeError.HTTP_ERROR, message)

    try:
        json_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error("{}: Invalid JSON response: {}", node_address, e)
        return NodeResult(node_address, NodeError.INVALID_RESPONSE, response_text)

    try:
        node_info = load_system_info(json_data)
    except Exception as e:
        logger.error("{}: Parsing node information failed: {}", node_address, e)
        return NodeResult(node_address, NodeError.PARSE_ERROR, response_text)

    logger.success("Finished polling {}", node_info)
    return NodeResult(node_address, node_info, response_text)


async def _get_node_links(olsr_records: AsyncIterable[str]) -> AsyncIterator[LinkInfo]:
    """Process OLSR records, yielding the link information between nodes in the network.

    Based on `wxc_netcat()` in MeshMap the only lines we are interested in
    (when getting the node list)
    are the ones that look like this:

        "10.32.66.190" -> "10.80.213.95"[label="1.000"];

    Records where the second address is in CIDR notation and the label is "HNA" should
    be excluded via a regular expression for the above.

    Args:
        olsr_records: Asynchronous iterable of lines from the

    Yields:


    """
    count: DefaultDict[str, int] = defaultdict(int)
    # apparently there have been issues with duplicate links
    # so track the ones that have been returned
    links_returned = set()
    link_regex = re.compile(
        r"^\"(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\" -> "
        r"\"(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\"\[label=\"(.+?)\"\];"
    )

    async for line in olsr_records:
        count["lines processed"] += 1

        match = link_regex.match(line)
        if not match:
            count["lines skipped"] += 1
            continue
        logger.trace(line)
        source_node = match.group(1)
        destination_node = match.group(2)
        label = match.group(3)
        if (source_node, destination_node) in links_returned:
            logger.debug("Duplicate link: {}", (source_node, destination_node, label))
            count["duplicate link"] += 1
            continue
        links_returned.add((source_node, destination_node))
        count["links returned"] += 1
        yield LinkInfo.from_strings(source_node, destination_node, label)

    logger.info("OLSR Link Statistics: {}", dict(count))
    if count["links returned"] == 0:
        logger.warning(
            "Failed to find any links in {:,d} lines of OLSR data.",
            count["lines processed"],
        )

    return
