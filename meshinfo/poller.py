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
from asyncio import StreamReader
from collections import abc, defaultdict, deque
from collections.abc import Iterable, Iterator
from typing import Awaitable, NamedTuple

import aiohttp
import attrs
import structlog
from structlog import contextvars

from .aredn import LinkInfo, SystemInfo, load_system_info
from .types import LinkType

logger = structlog.get_logger()


@attrs.frozen
class TopoLink:
    """Basic link information available from topology."""

    source: str
    destination: str
    cost: float = attrs.field(eq=False)

    @classmethod
    def from_strings(cls, source: str, destination: str, label: str) -> TopoLink:
        """Create object from strings in OLSR data."""
        cost = 99.99 if label == "INFINITE" else float(label)
        return cls(source, destination, cost)

    def __str__(self):
        return f"{self.source} -> {self.destination} ({self.cost})"


@attrs.define
class Topology:
    """Model basic topology information about the network."""

    nodes: set[str] = attrs.Factory(set)
    """Set of IP addresses of all nodes on the network."""
    links_by_source: dict[str, set[TopoLink]] = attrs.Factory(lambda: defaultdict(set))
    """Link information, organized by source IP address."""

    @property
    def links(self) -> Iterator[TopoLink]:
        for links in self.links_by_source.values():
            yield from links


async def topology_from_olsr(
    host_name: str = "localnode.local.mesh", port: int = 2004, timeout: int = 5
) -> Topology:
    """Load a model of the topology from the OLSR daemon.

    Connects to the OLSR daemon on the specified host and parses the response.
    """
    with contextvars.bound_contextvars(host=host_name, port=port):
        logger.debug("Connecting to OLSR daemon for topology data")
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host_name, port), timeout
            )
        except asyncio.TimeoutError as exc:
            logger.error("OLSR timeout")
            raise RuntimeError("Timeout connecting to OLSR daemon") from exc
        except OSError as exc:
            # Connection errors subclass `OSError`
            logger.error("OLSR connection error", error=exc)
            raise RuntimeError("Failed to connect to OLSR daemon") from exc

        topology = await _process_olsr_data(reader)

        writer.close()
        await writer.wait_closed()
    return topology


async def _process_olsr_data(reader: StreamReader) -> Topology:
    """Parse OLSR data into model of topology.

    Based on `wxc_netcat()` in MeshMap the only lines we are interested in
    (when getting the node list)
    are the ones that look like this:

        "10.32.66.190" -> "10.80.213.95"[label="1.000"];

    Records where the second address is in CIDR notation and the label is "HNA"
    should be excluded via a regular expression for the above.
    """
    node_regex = re.compile(r"^\"(\d{2}\.\d{1,3}\.\d{1,3}\.\d{1,3})\" -> \"\d+")
    link_regex = re.compile(
        r"^\"(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\" -> "
        r"\"(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\"\[label=\"(.+?)\"\];"
    )
    topology = Topology()
    while line_bytes := await reader.readline():
        line = line_bytes.decode("utf-8").rstrip()
        if match := node_regex.match(line):
            topology.nodes.add(match[1])
        if match := link_regex.match(line):
            link = TopoLink.from_strings(*match.group(1, 2, 3))
            topology.links_by_source[link.source].add(link)
    logger.info(
        "Loaded topology from OLSR",
        node_count=len(topology.nodes),
        link_count=len(list(topology.links)),
    )
    return topology


@attrs.define
class Poller:
    max_connections: int
    timeout: aiohttp.ClientTimeout
    lookup_name: abc.Callable[[str], Awaitable[str]]

    @classmethod
    def create(
        cls,
        lookup_name: abc.Callable[[str], Awaitable[str]],
        max_connections: int = 50,
        connect_timeout: int = 10,
        read_timeout: int = 15,
    ) -> Poller:
        """Initialize a `Poller` object."""
        return Poller(
            lookup_name=lookup_name,
            max_connections=max_connections,
            timeout=aiohttp.ClientTimeout(
                sock_connect=connect_timeout,
                sock_read=read_timeout,
            ),
        )

    async def get_network_info(self, topology: Topology) -> NetworkInfo:
        """Gets the node and link information about the network."""

        # start processing the nodes
        node_task = asyncio.create_task(self._poll_nodes(topology.nodes))
        # wait for the nodes to finish processing
        node_results: list[NodeResult] = await node_task

        # make a dictionary for quick lookups of node name from IP address
        # (for cross-referencing with OLSR data)
        ip_name_map = {
            node.ip_address: node.name
            for node in node_results
            if all((node.name, node.ip_address))
        }

        count: defaultdict[str, int] = defaultdict(int)
        # Collect the list of node `SystemInfo` objects to return
        nodes: deque[SystemInfo] = deque()
        # Build list of links for all nodes, using AREDN data, falling back to OLSR
        links: deque[LinkInfo] = deque()
        node_errors: deque[NodeResult] = deque()
        for node in node_results:
            count["node results"] += 1
            if node.error:
                count["errors (totals)"] += 1
                count[f"errors ({node.error.error!s})"] += 1
                node_errors.append(node)
                continue

            sys_info = node.system_info
            if sys_info is None:
                logger.error("Node does not have response or error", node=node)
                continue
            nodes.append(sys_info)
            if len(sys_info.links) > 0:
                # Use link information from AREDN if we have it (newer firmware)
                count["using link_info json"] += 1
                if sys_info.api_version_tuple < (1, 9):
                    # get the link cost from OLSR (pre-v1.9 API)
                    count["using olsr for link cost"] += 1
                    _populate_link_cost_from_topography(
                        sys_info.links,
                        topology.links_by_source.get(node.ip_address, set()),
                    )
                links.extend(sys_info.links)
                sys_info.link_count = len(sys_info.links)
                continue

            # Create `LinkInfo` objects based on the information in OLSR
            # **This should only necessary for firmware < API 1.7**
            count["using olsr for link data"] += 1
            sys_info.link_count = 0
            try:
                node_olsr_links = topology.links_by_source[node.ip_address]
            except KeyError:
                logger.warning(
                    "Failed to find OLSR link(s)",
                    system_info=sys_info,
                    ip_address=node.ip_address,
                )
                continue
            for link in node_olsr_links:
                sys_info.link_count += 1
                if link.destination not in ip_name_map:
                    logger.warning(
                        "OLSR IP not found in node information, skipping",
                        link=link,
                    )
                    continue
                links.append(
                    LinkInfo(
                        source=sys_info.node_name,
                        destination=ip_name_map[link.destination],
                        destination_ip=link.destination,
                        type=LinkType.UNKNOWN,
                        interface="unknown",
                        olsr_cost=link.cost,
                    )
                )

        logger.info("Finished loading network data", summary=dict(count))

        return NetworkInfo(nodes, links, node_errors)

    async def _poll_nodes(self, addresses: Iterable[str]) -> list[NodeResult]:
        """Get information about all the nodes in the network."""
        start_time = time.monotonic()

        tasks = []
        connector = aiohttp.TCPConnector(limit=self.max_connections)
        async with aiohttp.ClientSession(
            timeout=self.timeout, connector=connector
        ) as session:
            for address in addresses:
                with contextvars.bound_contextvars(ip=address):
                    task = asyncio.create_task(
                        self._poll_node(address, session=session)
                    )
                    # Since aiohttp is handling limits,
                    # these all get created at the beginning,
                    # not close to when they are actually processed.
                    # logger.debug("Created polling task")
                    tasks.append(task)

            # collect all the results in a single list, dropping any exceptions
            node_results = []
            for result in await asyncio.gather(*tasks, return_exceptions=True):
                if isinstance(result, Exception):
                    logger.error("Unexpected exception polling nodes", error=result)
                    continue
                node_results.append(result)

        crawler_finished = time.monotonic()
        logger.info("Querying nodes finished", elapsed=crawler_finished - start_time)
        return node_results

    async def _poll_node(
        self, ip_address: str, *, session: aiohttp.ClientSession
    ) -> NodeResult:
        """Query a node via HTTP to get the information about that node.

        Args:
            session: aiohttp session object
                (docs recommend to pass around single object)
            ip_address: IP address of the node to query

        Returns:
            Named tuple with the IP address,
            result of either `SystemInfo` or `NodeError`,
            and the raw response string.

        """

        params = {"services_local": 1, "link_info": 1}

        try:
            async with session.get(
                f"http://{ip_address}:8080/cgi-bin/sysinfo.json", params=params
            ) as resp:
                logger.debug("HTTP response received")
                status = resp.status
                response = await resp.read()
                # copy and pasting Unicode seems to create an invalid description
                # example we had was b"\xb0" for a degree symbol
                response_text = response.decode("utf-8", "replace")
        except Exception as exc:
            return await self._handle_connection_error(ip_address, exc)

        if status != 200:
            message = f"{status}: {response_text}"
            return await self._handle_response_error(
                ip_address, PollingError.HTTP_ERROR, message
            )

        try:
            json_data = json.loads(response_text)
        except json.JSONDecodeError as exc:
            return await self._handle_response_error(
                ip_address, PollingError.INVALID_RESPONSE, response_text, exc
            )

        try:
            node_info = load_system_info(json_data)
        except Exception as exc:
            return await self._handle_response_error(
                ip_address, PollingError.PARSE_ERROR, response_text, exc
            )

        logger.debug("Finished polling", name=node_info.node_name)
        return NodeResult(
            ip_address=ip_address,
            name=node_info.node_name,
            system_info=node_info,
        )

    async def _handle_connection_error(
        self, ip_address: str, exc: Exception
    ) -> NodeResult:
        result = NodeResult(
            ip_address=ip_address,
            name=await self.lookup_name(ip_address),
        )
        contextvars.bind_contextvars(node=result.name)

        # py3.10 - use match operator?
        if isinstance(exc, asyncio.TimeoutError):
            # catch this first, because some exceptions use multiple inheritance
            logger.warning("Connection timeout", exc=exc)
            result.error = NodeError(PollingError.TIMEOUT_ERROR, "Timeout error")
        elif isinstance(exc, aiohttp.ClientError):
            logger.warning("Connection error", exc=exc)
            result.error = NodeError(PollingError.CONNECTION_ERROR, str(exc))
        else:
            logger.warning("Unknown error", exc=exc)
            result.error = NodeError(PollingError.CONNECTION_ERROR, str(exc))

        return result

    async def _handle_response_error(
        self,
        ip_address: str,
        error: PollingError,
        response: str,
        exc: Exception | None = None,
    ) -> NodeResult:
        node_name = await self.lookup_name(ip_address)
        result = NodeResult(ip_address=ip_address, name=node_name)
        contextvars.bind_contextvars(node=node_name)

        # py3.10 - use match operator?
        if error == PollingError.HTTP_ERROR:
            logger.warning("HTTP error", response=response)
            result.error = NodeError(PollingError.HTTP_ERROR, response)
        elif error == PollingError.INVALID_RESPONSE:
            logger.warning("Invalid JSON response", exc=exc)
            result.error = NodeError(PollingError.INVALID_RESPONSE, response)
        elif error == PollingError.PARSE_ERROR:
            logger.warning("Parsing node information failed", exc=exc)
            result.error = NodeError(PollingError.PARSE_ERROR, response)

        return result


def _populate_link_cost_from_topography(
    links: list[LinkInfo], olsr_links: set[TopoLink]
):
    """Populate the link cost from the topology data."""
    if len(olsr_links) == 0:
        logger.warning("No OLSR link data found", source=links[0].source)
        return
    cost_by_destination = {link.destination: link.cost for link in olsr_links}
    for link in links:
        if link.destination_ip not in cost_by_destination:
            continue
        link.olsr_cost = cost_by_destination[link.destination_ip]


class NetworkInfo(NamedTuple):
    """Combined results of querying the nodes and links on the network.

    Errors are stored as a dictionary, indexed by the IP address and storing the error
    and any message in a tuple.

    """

    nodes: deque[SystemInfo]
    links: deque[LinkInfo]
    errors: deque[NodeResult]


@attrs.define
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


@attrs.define
class NodeResult:
    ip_address: str
    name: str
    system_info: SystemInfo | None = None
    error: NodeError | None = None

    @property
    def label(self) -> str:
        return f"{self.name or 'name unknown'} ({self.ip_address})"
