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
from asyncio import Queue, StreamReader
from collections import defaultdict, deque
from collections.abc import Iterator
from typing import NamedTuple

import aiohttp
import attrs
import structlog
from structlog import contextvars

from .aredn import LinkInfo, SystemInfo, load_system_info
from .network import reverse_dns_lookup
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


class NetworkInfo(NamedTuple):
    """Combined results of querying the nodes and links on the network."""

    nodes: deque[SystemInfo]
    links: deque[LinkInfo]
    errors: deque[NodeError]


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
class NodeError:
    ip_address: str
    name: str
    error: PollingError
    response: str

    @property
    def label(self) -> str:
        return f"{self.name or 'name unknown'} ({self.ip_address})"

    def __str__(self):
        return f"{self.error} ('{self.response[10:]}...')"


async def topology_from_olsr(
    host_name: str, port: int = 2004, timeout: int = 5
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


async def poll_network(
    *,
    start_node: str,
    timeout: int,
    workers: int,
    dns_server: str = "",
) -> NetworkInfo:
    """Loads topology data from the specified node and then polls the network.

    Returns:
        System information for all successfully parsed nodes,
        link information for all the links,
        and errors encountered contacting/parsing node data.

    """
    try:
        topology = await _get_network_hosts(start_node)
    except Exception as exc:
        logger.warning("Error getting node list from `sysinfo.json`", error=exc)
        topology = await topology_from_olsr(start_node)

    dns_server = dns_server or start_node

    queue: asyncio.Queue[str] = asyncio.Queue()
    for ip_address in topology.nodes:
        queue.put_nowait(ip_address)

    results = NetworkInfo(deque(), deque(), deque())

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=0),
        timeout=aiohttp.ClientTimeout(total=timeout),
    ) as session:
        start_time = time.monotonic()
        worker_tasks = []
        for id_ in range(workers):
            with contextvars.bound_contextvars(worker=id_):
                worker_tasks.append(
                    asyncio.create_task(
                        _node_polling_worker(queue, results, session, dns_server)
                    )
                )

        await queue.join()
        crawler_elapsed = time.monotonic() - start_time

        for task in worker_tasks:
            task.cancel()

        await asyncio.gather(*worker_tasks, return_exceptions=True)
        logger.info("Querying nodes finished", elapsed=crawler_elapsed)

    # make a dictionary for quick lookups of node name from IP address
    # (for cross-referencing with OLSR data)
    ip_name_map = {
        node.ip_address: node.node_name
        for node in results.nodes
        if all((node.node_name, node.ip_address))
    }

    count: defaultdict[str, int] = defaultdict(int)
    for error in results.errors:
        if all((error.name, error.ip_address)):
            ip_name_map[error.ip_address] = error.name
        count["errors (totals)"] += 1
        count[f"errors ({error.error!s})"] += 1

    for sys_info in results.nodes:
        count["node results"] += 1

        if len(sys_info.links) == 0:
            # Create `LinkInfo` objects based on the information in OLSR
            # **This should only necessary for firmware < API 1.7**
            count["using olsr for link data"] += 1
            results.links.extend(
                _create_link_info_from_topology(sys_info, topology, ip_name_map)
            )
            continue

        # Use link information from AREDN if we have it (API >= 1.7)
        count["using link_info json"] += 1
        if sys_info.api_version_tuple < (1, 9):
            # get the link cost from OLSR (pre-v1.9 API)
            count["using olsr for link cost"] += 1
            _populate_link_cost_from_topography(
                sys_info.links,
                topology.links_by_source.get(sys_info.ip_address, set()),
            )
        results.links.extend(sys_info.links)
        sys_info.link_count = len(sys_info.links)
        continue

    logger.info("Finished loading network data", summary=dict(count))
    return results


async def _get_network_hosts(host_name: str) -> Topology:
    """Load the list of hosts from AREDN API.

    This does not provide link information (unlike OLSR),
    but the API provides all that data now, so this is the future,
    especially since we can no longer access OLSR directly.

    """
    # TODO: drop all OLSR dependency and use this to
    #  return IP addresses *and* host names (#131)
    with contextvars.bound_contextvars(host=host_name):
        logger.debug("Fetching network host information from AREDN API")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{host_name}/cgi-bin/sysinfo.json", params={"topology": 1}
            ) as response:
                results = await response.json()

        # Using `topology` instead of `hosts` because that includes non-AREDN nodes
        # (which cause extra connection/parsing issues).
        topology = Topology(
            nodes={entry["destinationIP"] for entry in results["topology"]}
        )

    return topology


async def _node_polling_worker(
    queue: Queue, results: NetworkInfo, session: aiohttp.ClientSession, dns_server: str
) -> None:
    """Asynchronous worker to process nodes from the queue and poll them."""
    while True:
        ip_address = await queue.get()
        start_time = time.monotonic()
        with contextvars.bound_contextvars(node_ip=ip_address):
            logger.debug("Began polling")
            node_info = await _poll_node(ip_address, session, dns_server=dns_server)
            elapsed = time.monotonic() - start_time
            if isinstance(node_info, SystemInfo):
                logger.debug(
                    "Finished polling", name=node_info.node_name, elapsed=elapsed
                )
                results.nodes.append(node_info)
            else:
                logger.debug(
                    "Finished polling (with errors)",
                    name=node_info.name,
                    elapsed=elapsed,
                )
                results.errors.append(node_info)
        queue.task_done()


async def _poll_node(
    ip_address: str, session: aiohttp.ClientSession, *, dns_server: str
) -> SystemInfo | NodeError:
    """Fetch a node's ``sysinfo.json`` and attempt to parse the response."""
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
    except asyncio.TimeoutError as exc:
        node_name = await reverse_dns_lookup(ip_address, dns_server)
        logger.warning("Connection timeout", name=node_name, exc=exc)
        return NodeError(ip_address, node_name, PollingError.TIMEOUT_ERROR, str(exc))
    except aiohttp.ClientError as exc:
        node_name = await reverse_dns_lookup(ip_address, dns_server)
        logger.warning("Connection error", name=node_name, exc=exc)
        return NodeError(ip_address, node_name, PollingError.CONNECTION_ERROR, str(exc))
    except Exception as exc:
        node_name = await reverse_dns_lookup(ip_address, dns_server)
        logger.warning("Unknown error", name=node_name, exc=exc)
        return NodeError(ip_address, node_name, PollingError.CONNECTION_ERROR, str(exc))

    if status != 200:
        message = f"{status}: {response_text}"
        node_name = await reverse_dns_lookup(ip_address, dns_server)
        logger.warning("HTTP error", name=node_name, response=message)
        return NodeError(ip_address, node_name, PollingError.HTTP_ERROR, message)

    try:
        json_data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        node_name = await reverse_dns_lookup(ip_address, dns_server)
        logger.warning("Invalid JSON response", name=node_name, exc=exc)
        return NodeError(
            ip_address, node_name, PollingError.INVALID_RESPONSE, response_text
        )

    try:
        node_info = load_system_info(json_data, ip_address=ip_address)
    except Exception as exc:
        node_name = await reverse_dns_lookup(ip_address, dns_server)
        logger.warning("Parsing node information failed", name=node_name, exc=exc)
        return NodeError(ip_address, node_name, PollingError.PARSE_ERROR, response_text)

    return node_info


def _create_link_info_from_topology(
    sys_info: SystemInfo, topology: Topology, ip_name_map: dict[str, str]
) -> Iterator[LinkInfo]:
    """Yield link information from the topology data for older firmware versions."""
    sys_info.link_count = 0
    try:
        node_olsr_links = topology.links_by_source[sys_info.ip_address]
    except KeyError:
        logger.warning(
            "Failed to find OLSR link(s)",
            system_info=sys_info,
            ip_address=sys_info.ip_address,
        )
        return
    for link in node_olsr_links:
        sys_info.link_count += 1
        if link.destination not in ip_name_map:
            logger.warning(
                "OLSR IP not found in node information, skipping",
                link=link,
            )
            continue
        yield LinkInfo(
            source=sys_info.node_name,
            destination=ip_name_map[link.destination],
            destination_ip=link.destination,
            type=LinkType.UNKNOWN,
            interface="unknown",
            olsr_cost=link.cost,
        )


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
