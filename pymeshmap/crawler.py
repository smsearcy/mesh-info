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
import html
import json
import re
import time
from collections import defaultdict
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    DefaultDict,
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

# these are defined as constants at the module level so they are only initialized once
# (if the set was initialize for each function then it wouldn't be faster)
NINE_HUNDRED_MHZ_BOARDS = {"0xe009", "0xe1b9", "0xe239"}
TWO_GHZ_CHANNELS = {"-1", "-2", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"}
# according to MeshMap sometimes it will show channel, sometimes frequency
THREE_GHZ_CHANNELS = {
    "76",
    "77",
    "78",
    "79",
    "80",
    "81",
    "82",
    "83",
    "84",
    "85",
    "86",
    "87",
    "88",
    "89",
    "90",
    "91",
    "92",
    "93",
    "94",
    "95",
    "96",
    "97",
    "98",
    "99",
    "3380",
    "3385",
    "3390",
    "3395",
    "3400",
    "3405",
    "3410",
    "3415",
    "3420",
    "3425",
    "3430",
    "3435",
    "3440",
    "3445",
    "3450",
    "3455",
    "3460",
    "3465",
    "3470",
    "3475",
    "3480",
    "3485",
    "3490",
    "3495",
}
# per MeshMap 133+ are US channel numbers, info taken from "channelmaps.pm" in AREDEN
FIVE_GHZ_CHANNELS = {
    "37",
    "40",
    "44",
    "48",
    "52",
    "56",
    "60",
    "64",
    "100",
    "104",
    "108",
    "112",
    "116",
    "120",
    "124",
    "128",
    "132",
    "133",
    "134",
    "135",
    "136",
    "137",
    "138",
    "139",
    "140",
    "141",
    "142",
    "143",
    "144",
    "145",
    "146",
    "147",
    "148",
    "149",
    "150",
    "151",
    "152",
    "153",
    "154",
    "155",
    "156",
    "157",
    "158",
    "159",
    "160",
    "161",
    "162",
    "163",
    "164",
    "165",
    "166",
    "167",
    "168",
    "169",
    "170",
    "171",
    "172",
    "173",
    "174",
    "175",
    "176",
    "177",
    "178",
    "179",
    "180",
    "181",
    "182",
    "183",
    "184",
}

# TODO: make this a configuration variable
HTTP_MAX_CONNECTIONS = 100  # 100 is the default in aiohttp


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


@attr.s(auto_attribs=True, slots=True)
class Interface:
    """Data class to represent the individual interfaces on a node."""

    name: str
    mac_address: str
    ip_address: Optional[str] = None

    @classmethod
    def from_json(cls, raw_data: Dict[str, str]) -> Interface:
        return cls(
            name=raw_data["name"],
            # some tunnel interfaces lack a MAC address
            mac_address=raw_data.get("mac", ""),
            ip_address=raw_data.get("ip") if raw_data.get("ip") != "none" else None,
        )


@attr.s(auto_attribs=True, slots=True)
class Service:
    """Data class to represent the individual services on a node."""

    name: str
    protocol: str
    link: str

    @classmethod
    def from_json(cls, raw_data: Dict[str, str]) -> Service:
        return cls(
            name=raw_data["name"], protocol=raw_data["protocol"], link=raw_data["link"]
        )


@attr.s(slots=True)
class SystemInfo:
    """Data class to represent the node data from 'sysinfo.json'.

    Data that is directly retrieved from the node is stored in this class
    and "derived" data is then determined at runtime via property attributes
    (e.g. the wireless adaptor and band information).

    The network interfaces are represented by a dictionary,
    indexed by the interface name.

    For string values, missing data is typically stored as an empty string,
    particularly if an empty string would not be a valid value (e.g. SSID).
    If there is a situation in which missing/unknown values need to be distinguished
    from empty strings then `None` would be appropriate.
    In a case like node description it is an optional value
    so I see no need for "Unknown"/`None`.

    """

    node_name: str = attr.ib()
    api_version: str = attr.ib()
    grid_square: str = attr.ib()
    latitude: Optional[float] = attr.ib()
    longitude: Optional[float] = attr.ib()
    interfaces: Dict[str, Interface] = attr.ib()
    ssid: str = attr.ib()
    channel: str = attr.ib()
    channel_bandwidth: str = attr.ib()
    model: str = attr.ib()
    board_id: str = attr.ib()
    firmware_version: str = attr.ib()
    firmware_manufacturer: str = attr.ib()
    active_tunnel_count: int = attr.ib()
    tunnel_installed: bool = attr.ib()
    services: List[Service] = attr.ib()
    status: str = attr.ib()
    description: str = attr.ib(default="")
    frequency: str = attr.ib(default="")
    up_time: str = attr.ib(default="")
    load_averages: Optional[List[float]] = attr.ib(default=None)

    @property
    def lan_ip_address(self) -> str:
        iface_names = ["br-lan", "eth0"]
        for iface in iface_names:
            if iface not in self.interfaces or not self.interfaces[iface].ip_address:
                continue
            return self.interfaces[iface].ip_address or ""
        return ""

    @property
    def wifi_interface(self) -> Optional[Interface]:
        """Get the active wireless interface."""
        # is it worth using cached_property?
        iface_names = ["wlan0", "wlan1", "eth0.3975", "eth1.3975"]
        for iface in iface_names:
            if iface not in self.interfaces or not self.interfaces[iface].ip_address:
                continue
            return self.interfaces[iface]
        else:
            logger.warning("{}: failed to identify wireless interface", self.node_name)
            return None

    @property
    def wifi_ip_address(self) -> str:
        return getattr(self.wifi_interface, "ip_address", "")

    @property
    def wifi_mac_address(self) -> str:
        return getattr(self.wifi_interface, "mac_address", "")

    @property
    def band(self) -> str:
        if self.status != "on":
            return ""
        if self.board_id in NINE_HUNDRED_MHZ_BOARDS:
            return "900MHz"
        elif self.channel in TWO_GHZ_CHANNELS:
            return "2GHz"
        elif self.channel in THREE_GHZ_CHANNELS:
            return "3GHZ"
        elif self.channel in FIVE_GHZ_CHANNELS:
            return "5GHz"
        else:
            return "Unknown"

    def __str__(self):
        return f"{self.node_name} ({self.wifi_ip_address})"


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


async def network_info(
    host: str, *, addresses_to_ignore: Set[str] = None
) -> NetworkInfo:
    """Helper function to query node and link information asynchronously.

    Args:
        host: Host name or IP address to query the OLSR daemon for network information.
        addresses_to_ignore: Set of IP addresses to skip.

    Returns:
        Named tuple with a list of all the nodes successfully queried,
        a list of the links on the network,
        and a dictionary of errors keyed by the IP address.

    """

    node_task = asyncio.create_task(
        network_nodes(host, addresses_to_ignore=addresses_to_ignore)
    )
    # without a 1 second sleep here only one task was able to get data from OLSR
    # (but I'm on a small network)
    # if only one task can access that daemon at once then these will need to happen
    # sequentially (fortunately the links process is super fast)
    await asyncio.sleep(1)
    link_task = asyncio.create_task(network_links(host))

    nodes: NetworkNodes = await node_task
    links: List[LinkInfo] = await link_task

    return NetworkInfo(nodes.nodes, links, nodes.errors)


async def network_nodes(
    host: str, *, addresses_to_ignore: Set[str] = None
) -> NetworkNodes:
    """Asynchronously gets information for all the nodes on the network.

    Getting a list of the nodes is done via connecting to the OLSR

    Args:
        host: Host name or IP address to query the OLSR daemon for network information.
        addresses_to_ignore: Set of IP addresses to skip.

    Returns:
        Named tuple with a list of all the nodes successfully queried and
        a dictionary of errors keyed by the IP address.

    """
    start_time = time.monotonic()

    tasks: List[Awaitable] = []
    conn = aiohttp.TCPConnector(limit=HTTP_MAX_CONNECTIONS)
    async with aiohttp.ClientSession(connector=conn) as session:
        olsr_records = _query_olsr(host)
        async for node_address in _get_node_addresses(
            olsr_records, addresses_to_ignore=addresses_to_ignore
        ):
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


async def network_links(host: str) -> List[LinkInfo]:
    """Asynchronously gets information about all links between nodes in the network.

    This is rather simple because all that information is available
    from the OLSR daemon running on the local node.
    Since this function does not need to crawl the network
    there is less need to be asynchronous
    but this way we can re-use a single OLSR query function

    Args:
        host: Host name or IP address to query the OLSR daemon for network information.

    Returns:
        List of `LinkInfo` data classes for each unique link in the network.

    """

    olsr_records = _query_olsr(host)
    links = [link async for link in _get_node_links(olsr_records)]
    logger.info("Network link count: {}", len(links))
    return links


def _load_node_data(json_data: Dict[str, Any]) -> SystemInfo:
    """Convert data from `sysinfo.json` into a dataclass.

    Any exceptions due to parsing errors are passed to the caller.
    Extra/unknown fields in the source data are ignored.

    Args:
        json_data: Python dictionary loaded from the JSON data.

    Returns:
        Data class with information about the node.

    """

    interfaces = [
        Interface.from_json(iface_data) for iface_data in json_data["interfaces"]
    ]

    # create a dictionary with all the parameters due to the number
    # and variance between API versions
    data = {
        "node_name": json_data["node"],
        "api_version": json_data["api_version"],
        "grid_square": json_data["grid_square"],
        "latitude": float(json_data["lat"]) if json_data["lat"] else None,
        "longitude": float(json_data["lon"]) if json_data["lon"] else None,
        "interfaces": {iface.name: iface for iface in interfaces},
        "services": [
            Service.from_json(service_data)
            for service_data in json_data.get("services_local", [])
        ],
    }

    # generally newer versions add data in nested dictionaries
    # sometimes that data was present at the root level in older versions

    if "sysinfo" in json_data:
        data["up_time"] = json_data["sysinfo"]["uptime"]
        data["load_averages"] = [float(load) for load in json_data["sysinfo"]["loads"]]

    if "meshrf" in json_data:
        meshrf = json_data["meshrf"]
        data["status"] = meshrf.get("status", "on")
        #
        data["ssid"] = meshrf.get("ssid", "")
        data["channel"] = meshrf.get("channel", "")
        data["channel_bandwidth"] = meshrf.get("chanbw", "")
        data["frequency"] = meshrf.get("freq", "")
    else:
        data["ssid"] = json_data["ssid"]
        data["channel"] = json_data["channel"]
        data["channel_bandwidth"] = json_data["chanbw"]
        data["status"] = "on"

    if "node_details" in json_data:
        details = json_data["node_details"]
        data["description"] = html.unescape(details.get("description", ""))
        data["firmware_version"] = details["firmware_version"]
        data["firmware_manufacturer"] = details["firmware_mfg"]
        data["model"] = details["model"]
        data["board_id"] = details["model"]
    else:
        data["firmware_version"] = json_data["firmware_version"]
        data["firmware_manufacturer"] = json_data["firmware_mfg"]
        data["model"] = json_data["model"]
        data["board_id"] = json_data["model"]

    if "tunnels" in json_data:
        tunnels = json_data["tunnels"]
        data["active_tunnel_count"] = int(tunnels["active_tunnel_count"])
        data["tunnel_installed"] = tunnels["tunnel_installed"]
    else:
        data["active_tunnel_count"] = int(json_data["active_tunnel_count"])
        # "tunnel_installed" is a string in API 1.0
        if isinstance(json_data["tunnel_installed"], bool):
            data["tunnel_installed"] = json_data["tunnel_installed"]
        else:
            data["tunnel_installed"] = json_data["tunnel_installed"].lower() == "true"

    return SystemInfo(**data)


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


async def _get_node_addresses(
    olsr_records: AsyncIterable[str], *, addresses_to_ignore: Set[str] = None
) -> AsyncIterator[str]:
    """Process OLSR records, yielding the IP addresses of nodes in the network.

    Based on `wxc_netcat()` in MeshMap the only lines we are interested in
    (when getting the node list)
    are the ones that look (generally) like this
    (sometimes the second address is a CIDR address):

        "10.32.66.190" -> "10.80.213.95"[label="1.000"];

    """
    addresses_to_ignore = addresses_to_ignore or set()
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
        if node_address in addresses_to_ignore:
            count["ignored node"] += 1
            continue
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
            response_text = await resp.text()
    except aiohttp.ClientError as e:
        logger.error("{}: Connection issue: {}", node_address, e)
        return NodeResult(node_address, NodeError.CONNECTION_ERROR, str(e))
    except asyncio.TimeoutError:
        logger.error("{}: Timeout attempting to connect", node_address)
        return NodeResult(node_address, NodeError.TIMEOUT_ERROR, "Timeout error")
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
        node_info = _load_node_data(json_data)
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
