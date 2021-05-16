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
from asyncio import Lock, StreamReader, StreamWriter
from collections import defaultdict, deque
from typing import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    DefaultDict,
    Deque,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

import aiohttp
import attr
from loguru import logger

from .aredn import LinkType, SystemInfo, load_system_info
from .config import AppConfig


async def run(config: AppConfig.Poller) -> NetworkInfo:
    """Helper function for polling the network."""

    olsr = await OlsrData.connect(config.node)
    poller = Poller.from_config(config)
    return await poller.network_info(olsr)


class OlsrData:
    """Provides access to the nodes and links available in the OLSR data."""

    NODE_REGEX = re.compile(r"^\"(\d{2}\.\d{1,3}\.\d{1,3}\.\d{1,3})\" -> \"\d+")
    LINK_REGEX = re.compile(
        r"^\"(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\" -> "
        r"\"(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\"\[label=\"(.+?)\"\];"
    )

    class LineGenerator:
        def __init__(self, olsr: OlsrData, lock: Lock):
            self._olsr = olsr
            self._lock = lock
            self.queue: Deque[Union[str, LinkInfo]] = deque()

        def __aiter__(self):
            return self

        async def __anext__(self):
            if len(self.queue) > 0:
                return self.queue.popleft()

            while len(self.queue) == 0 and not self._olsr.finished:
                async with self._lock:
                    await self._olsr._populate_queues()

            if self._olsr.finished:
                raise StopAsyncIteration()

            return self.queue.popleft()

    def __init__(self, reader: StreamReader, writer: StreamWriter):
        self.reader = reader
        self.writer = writer
        self.finished = False
        olsr_lock = Lock()
        self.nodes: AsyncIterator[str] = self.LineGenerator(self, olsr_lock)
        self.links: AsyncIterator[LinkInfo] = self.LineGenerator(self, olsr_lock)
        self.stats: DefaultDict[str, int] = defaultdict(int)
        self._nodes_seen: Set[str] = set()
        self._links_seen: Set[Tuple[str, str, str]] = set()

    @classmethod
    async def connect(
        cls, host_name: str = "localnode.local.mesh", port: int = 2004, timeout: int = 5
    ) -> OlsrData:
        """Connect to an OLSR daemon and create an `OlsrData` wrapper.

        Args:
            host_name: Name of host to connect to OLSR daemon
            port: Port the OLSR daemon is running on
            timeout: Connection timeout in seconds

        """
        logger.trace("Connecting to OLSR daemon {}:{}", host_name, port)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host_name, port), timeout
            )
        except asyncio.TimeoutError:
            logger.error("Timeout attempting to connect to {}:{}", host_name, port)
            raise RuntimeError("Timeout connecting to OLSR daemon")
        except OSError as e:
            # Connection errors subclass `OSError`
            logger.error("Failed to connect to {}:{} ({!s})", host_name, port, e)
            raise RuntimeError("Failed to connect to OLSR daemon")

        return cls(reader, writer)

    async def _populate_queues(self):
        """Read data from OLSR and store for processing nodes and links."""

        if self.finished:
            return

        line_bytes = await self.reader.readline()
        if not line_bytes:
            # All data from OLSR has been processed
            self.finished = True
            self.writer.close()
            await self.writer.wait_closed()

            logger.info("OLSR Data Statistics: {}", dict(self.stats))
            if self.stats["nodes returned"] == 0:
                logger.warning(
                    "Failed to find any nodes in {:,d} lines of OLSR data.",
                    self.stats["lines processed"],
                )
            if self.stats["links returned"] == 0:
                logger.warning(
                    "Failed to find any links in {:,d} lines of OLSR data.",
                    self.stats["lines processed"],
                )
            return

        # TODO: filter until a useful line is present?
        self.stats["lines processed"] += 1
        line_str = line_bytes.decode("utf-8").rstrip()
        logger.trace("OLSR data: {}", line_str)

        # TODO: Use walrus operator when Python 3.8 is the minimum requirement
        node_address = self._get_address(line_str)
        if node_address:
            self.nodes.queue.append(node_address)
        link = self._get_link(line_str)
        if link:
            self.links.queue.append(link)

        return

    def _get_address(self, line: str) -> str:
        """Return the IP address of unique nodes from OLSR data lines.

        Based on `wxc_netcat()` in MeshMap the only lines we are interested in
        (when getting the node list)
        are the ones that look (generally) like this
        (sometimes the second address is a CIDR address):

            "10.32.66.190" -> "10.80.213.95"[label="1.000"];

        """
        match = self.NODE_REGEX.match(line)
        if not match:
            return ""

        node_address = match.group(1)
        if node_address in self._nodes_seen:
            self.stats["duplicate node"] += 1
            return ""
        self._nodes_seen.add(node_address)
        self.stats["nodes returned"] += 1
        return node_address

    def _get_link(self, line: str) -> Optional[LinkInfo]:
        """Return the IP addresses and cost of a link from an OLSR data line.

        Based on `wxc_netcat()` in MeshMap the only lines we are interested in
        (when getting the node list)
        are the ones that look like this:

            "10.32.66.190" -> "10.80.213.95"[label="1.000"];

        Records where the second address is in CIDR notation and the label is "HNA"
        should be excluded via a regular expression for the above.

        """
        match = self.LINK_REGEX.match(line)
        if not match:
            return None

        # apparently there have been issues with duplicate links
        # so track the ones that have been returned
        source_node = match.group(1)
        destination_node = match.group(2)
        label = match.group(3)

        link = (source_node, destination_node, label)
        if link in self._links_seen:
            self.stats["duplicate link"] += 1
            return None
        self._links_seen.add(link)
        self.stats["links returned"] += 1
        return LinkInfo.from_strings(*link)


@attr.s(auto_attribs=True)
class Poller:
    """Class to handle polling the network nodes and links.

    Mainly this is so we can initialize it with the configuration settings and then
    call them later.

    """

    max_connections: int
    connect_timeout: int
    read_timeout: int

    @classmethod
    def from_config(cls, config: AppConfig.Poller) -> Poller:
        return cls(
            max_connections=config.max_connections,
            connect_timeout=config.connect_timeout,
            read_timeout=config.read_timeout,
        )

    async def network_info(self, olsr_data: OlsrData) -> NetworkInfo:
        """Helper function to query node and link information asynchronously.

        Returns:
            Named tuple with a list of all the nodes successfully queried,
            a list of the links on the network,
            and a dictionary of errors keyed by the IP address.

        """

        node_task = asyncio.create_task(self.node_information(olsr_data.nodes))
        links = [link async for link in olsr_data.links]
        logger.info("Network link count: {}", len(links))

        node_results: NetworkNodes = await node_task
        nodes_by_ip, errors = node_results

        _add_extra_link_info(links, nodes_by_ip)

        return NetworkInfo(list(nodes_by_ip.values()), links, errors)

    async def node_information(
        self, node_addresses: AsyncIterable[str]
    ) -> NetworkNodes:
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
            sock_connect=self.connect_timeout,
            sock_read=self.read_timeout,
        )
        async with aiohttp.ClientSession(
            timeout=timeout, connector=connector
        ) as session:
            async for node_address in node_addresses:
                logger.debug("Creating task to poll {}", node_address)
                task = asyncio.create_task(_poll_node(session, node_address))
                tasks.append(task)

            # collect all the results in a single list
            node_results: List[Tuple[str, NodeResult]] = await asyncio.gather(
                *tasks, return_exceptions=True
            )

        crawler_finished = time.monotonic()
        logger.info("Querying nodes took {:.2f} seconds", crawler_finished - start_time)

        nodes = {}
        errors = {}
        count: DefaultDict[str, int] = defaultdict(int)
        for result in node_results:
            count["total"] += 1
            if isinstance(result, Exception):
                # this shouldn't happen but just in case
                count["exceptions"] += 1
                logger.error("Unhandled exception polling a node: {!r}", result)
                continue
            ip_address, response = result
            if isinstance(response, NodeError):
                # this error would have already been logged
                count["errors (total)"] += 1
                count[f"errors ({response.error!s})"] += 1
                errors[ip_address] = response
                continue
            count["successes"] += 1
            nodes[ip_address] = response

        logger.info("Network nodes summary: {}", dict(count))
        return NetworkNodes(nodes, errors)


class NetworkInfo(NamedTuple):
    """Combined results of querying the nodes and links on the network.

    Errors are stored as a dictionary, indexed by the IP address and storing the error
    and any message in a tuple.

    """

    nodes: List[SystemInfo]
    links: List[LinkInfo]
    errors: Dict[str, NodeError]


class NetworkNodes(NamedTuple):
    """Results of querying the nodes on the network, indexed by the IP address."""

    nodes: Dict[str, SystemInfo]
    errors: Dict[str, NodeError]


@attr.s(auto_attribs=True)
class NodeError:
    error: PollingError
    response: str

    def __str__(self):
        return f"{self.error} ('{self.response[10:]}...')"


class PollingError(enum.Enum):
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


NodeResult = Union[SystemInfo, NodeError]


@attr.s(slots=True, auto_attribs=True)
class LinkInfo:
    """OLSR link information measuring the cost between nodes."""

    source: str
    destination: str
    cost: float
    type: Optional[LinkType] = None
    quality: Optional[float] = None
    neighbor_quality: Optional[float] = None
    signal: Optional[int] = None
    noise: Optional[int] = None
    tx_rate: Optional[float] = None
    rx_rate: Optional[float] = None

    @classmethod
    def from_strings(cls, source: str, destination: str, label: str) -> LinkInfo:
        cost = 99.99 if label == "INFINITE" else float(label)
        return cls(source, destination, cost)

    def __str__(self):
        return f"{self.source} -> {self.destination} ({self.cost})"


async def _poll_node(
    session: aiohttp.ClientSession, ip_address: str
) -> Tuple[str, NodeResult]:
    """Query a node via HTTP to get the information about that node.

    Args:
        session: aiohttp session object (docs recommend to pass around single object)
        ip_address: IP address of the node to query

    Returns:
        Named tuple with the IP address,
        result of either `SystemInfo` or `NodeError`,
        and the raw response string.

    """

    logger.debug("{} begin polling...", ip_address)

    params = {"services_local": 1, "link_info": 1}

    try:
        async with session.get(
            f"http://{ip_address}:8080/cgi-bin/sysinfo.json", params=params
        ) as resp:
            status = resp.status
            response = await resp.read()
            # copy and pasting Unicode seems to create an invalid description
            # example we had was b"\xb0" for a degree symbol
            response_text = response.decode("utf-8", "replace")
    except asyncio.TimeoutError as e:
        # catch this first, because some exceptions use multiple inheritance
        logger.error("{}: {}", ip_address, e)
        return ip_address, NodeError(PollingError.TIMEOUT_ERROR, "Timeout error")
    except aiohttp.ClientError as e:
        logger.error("{}: {}", ip_address, e)
        return ip_address, NodeError(PollingError.CONNECTION_ERROR, str(e))
    except Exception as e:
        logger.error("{}: Unknown error connecting: {!r}", ip_address, e)
        return ip_address, NodeError(PollingError.CONNECTION_ERROR, str(e))

    if status != 200:
        message = f"{status}: {response_text}"
        logger.error("{}: HTTP error {}", ip_address, message)
        return ip_address, NodeError(PollingError.HTTP_ERROR, message)

    try:
        json_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error("{}: Invalid JSON response: {}", ip_address, e)
        return ip_address, NodeError(PollingError.INVALID_RESPONSE, response_text)

    try:
        node_info = load_system_info(json_data)
    except Exception as e:
        logger.error("{}: Parsing node information failed: {}", ip_address, e)
        return ip_address, NodeError(PollingError.PARSE_ERROR, response_text)

    logger.success("Finished polling {}", node_info)
    return ip_address, node_info


def _add_extra_link_info(links: List[LinkInfo], nodes_by_ip: Dict[str, SystemInfo]):
    """Modifies the links in place, adding extra data."""

    count: DefaultDict[str, int] = defaultdict(int)
    for link in links:
        count["total"] += 1
        # Look up extra link information from the AREDN SystemInfo response
        if link.source not in nodes_by_ip:
            count["node not found"] += 1
            continue
        if link.destination not in nodes_by_ip[link.source].links:
            count["link not found"] += 1
            continue
        extra_info = nodes_by_ip[link.source].links[link.destination]
        count["updated"] += 1

        link.type = extra_info.type
        link.quality = extra_info.quality
        link.neighbor_quality = extra_info.neighbor_quality
        link.signal = extra_info.signal
        link.noise = extra_info.noise
        link.tx_rate = extra_info.tx_rate
        link.rx_rate = extra_info.rx_rate

    logger.info("Extra link summary: {}", dict(count))
