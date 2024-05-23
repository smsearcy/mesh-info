"""Define data and functionality related to radios and AREDN software."""

from __future__ import annotations

import html
import re
import typing
from functools import cached_property
from itertools import zip_longest
from typing import Any

import attr
import structlog

from .types import Band, LinkType

if typing.TYPE_CHECKING:
    from .config import AppConfig


logger = structlog.get_logger()
# these are defined as constants at the module level so they are only initialized once

# TODO: calculate the channels similar to how AREDN does it for `rf_channel_map`?
# https://github.com/aredn/aredn/blob/b006c1040a48bf4d8866ab764a86d56cdb0f46f5/files/www/cgi-bin/setup

NINE_HUNDRED_MHZ_BOARDS = {"0xe009", "0xe1b9", "0xe239"}
TWO_GHZ_CHANNELS = {
    "-4",
    "-3",
    "-2",
    "-1",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
}
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
    "131",
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


@attr.s(auto_attribs=True, slots=True)
class Interface:
    """Data class to represent the individual interfaces on a node."""

    name: str
    mac_address: str
    ip_address: str | None = None

    @classmethod
    def from_json(cls, raw_data: dict[str, str]) -> Interface:
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
    def from_json(cls, raw_data: dict[str, str]) -> Service:
        return cls(
            name=raw_data["name"], protocol=raw_data["protocol"], link=raw_data["link"]
        )


@attr.s(auto_attribs=True, slots=True)
class LinkInfo:
    """Data class to represent the link information available from AREDN.

    Source and destination nodes are identified by name.

    """

    source: str
    destination: str
    destination_ip: str
    type: LinkType
    interface: str
    quality: float | None = None
    neighbor_quality: float | None = None
    signal: int | None = None
    noise: int | None = None
    tx_rate: float | None = None
    rx_rate: float | None = None
    olsr_cost: float | None = None

    @classmethod
    def from_json(
        cls, raw_data: dict[str, Any], *, source: str, ip_address: str
    ) -> LinkInfo:
        """Construct the `Link` dataclass from the AREDN JSON information.

        Needs the name of the source node passed in as well.

        Args:
            source: Hostname of source node (lowercase, no domain)
            ip_address: IP address of link destination

        """
        # fix example of a DTD link that wasn't properly identified as such
        missing_dtd = (
            raw_data["linkType"] == "" and raw_data["olsrInterface"] == "br-dtdlink"
        )
        type_ = "DTD" if missing_dtd else raw_data["linkType"]
        try:
            link_type = getattr(LinkType, type_)
        except AttributeError as exc:
            logger.warning("Unknown link type", error=str(exc))
            link_type = LinkType.UNKNOWN

        # ensure consistent node names
        node_name = raw_data["hostname"].replace(".local.mesh", "").lstrip(".").lower()
        if (link_cost := raw_data.get("linkCost")) is not None and link_cost > 99.99:
            link_cost = 99.99

        return LinkInfo(
            source=source,
            destination=node_name,
            destination_ip=ip_address,
            type=link_type,
            interface=raw_data["olsrInterface"],
            quality=raw_data["linkQuality"],
            neighbor_quality=raw_data["neighborLinkQuality"],
            signal=raw_data.get("signal"),
            noise=raw_data.get("noise"),
            tx_rate=raw_data.get("tx_rate"),
            rx_rate=raw_data.get("rx_rate"),
            olsr_cost=link_cost,
        )


@attr.s(auto_attribs=True)
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

    node_name: str
    display_name: str
    api_version: str
    grid_square: str
    latitude: float | None
    longitude: float | None
    interfaces: dict[str, Interface]
    ssid: str
    channel: str
    channel_bandwidth: str
    model: str
    board_id: str
    firmware_version: str
    firmware_manufacturer: str
    active_tunnel_count: int
    services: list[Service]
    services_json: list[dict]
    status: str
    source_json: dict
    description: str = ""
    frequency: str = ""
    up_time: str = ""
    load_averages: list[float] | None = None
    links: list[LinkInfo] = attr.Factory(list)
    link_count: int | None = None
    connection_ip: str = ""

    @property
    def lan_ip_address(self) -> str:
        iface_names = ("br-lan", "eth0", "eth0.0")
        for iface in iface_names:
            if iface not in self.interfaces or not self.interfaces[iface].ip_address:
                continue
            return self.interfaces[iface].ip_address or ""
        return ""

    @cached_property
    def primary_interface(self) -> Interface | None:
        """Get the active wireless interface."""
        # FIXME: should this just be done once as part of parsing?
        # (that might simplify the `ip_address` property as well,
        # don't need `connection_ip` in this class)
        iface_names = ("wlan0", "wlan1", "eth0.3975", "eth1.3975", "br-nomesh")
        for iface in iface_names:
            if iface not in self.interfaces or not self.interfaces[iface].ip_address:
                continue
            return self.interfaces[iface]
        logger.warning("Unable to identify wireless interface")
        return None

    @property
    def ip_address(self) -> str:
        return getattr(self.primary_interface, "ip_address", self.connection_ip)

    @property
    def mac_address(self) -> str:
        return (
            getattr(self.primary_interface, "mac_address", "").replace(":", "").lower()
        )

    @property
    def band(self) -> Band:
        if self.status != "on":
            return Band.OFF
        if self.board_id in NINE_HUNDRED_MHZ_BOARDS:
            return Band.NINE_HUNDRED_MHZ
        elif self.channel in TWO_GHZ_CHANNELS:
            return Band.TWO_GHZ
        elif self.channel in THREE_GHZ_CHANNELS:
            return Band.THREE_GHZ
        elif self.channel in FIVE_GHZ_CHANNELS:
            return Band.FIVE_GHZ
        else:
            return Band.UNKNOWN

    @property
    def up_time_seconds(self) -> int | None:
        """Convert uptime string to seconds."""
        if self.up_time == "":
            return None
        match = re.match(r"^(\d+) days, (\d+):(\d+):(\d+)", self.up_time)
        if match is None:
            logger.warning("Failed to parse uptime string", value=self.up_time)
            return None

        days = int(match.group(1))
        hours = int(match.group(2))
        minutes = int(match.group(3))
        seconds = int(match.group(4))

        return 86_400 * days + 3_600 * hours + 60 * minutes + seconds

    @property
    def radio_link_count(self) -> int | None:
        if not self.links:
            # the absence of the data presumably means an older API and thus unknown
            return None
        return sum(1 for link in self.links if link.type == LinkType.RF)

    @property
    def dtd_link_count(self) -> int | None:
        if not self.links:
            # the absence of the data presumably means an older API and thus unknown
            return None
        return sum(1 for link in self.links if link.type == LinkType.DTD)

    @property
    def tunnel_link_count(self) -> int:
        if not self.links:
            # in the absence of the link info dictionary use the tunnel count
            return self.active_tunnel_count
        return sum(1 for link in self.links if link.type == LinkType.TUN)

    @property
    def api_version_tuple(self) -> tuple[int, ...]:
        try:
            return tuple(int(value) for value in self.api_version.split("."))
        except ValueError:
            logger.warning("Invalid version string", value=self.api_version)
            return 0, 0

    def __str__(self):
        return f"{self.node_name} ({self.ip_address})"


def load_system_info(json_data: dict[str, Any], *, ip_address: str = "") -> SystemInfo:
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
        "connection_ip": ip_address,
        "node_name": json_data["node"].lower(),
        "display_name": json_data["node"],
        "api_version": json_data["api_version"],
        "grid_square": json_data.get("grid_square", ""),
        "latitude": float(json_data["lat"]) if json_data.get("lat") else None,
        "longitude": float(json_data["lon"]) if json_data.get("lon") else None,
        "interfaces": {iface.name: iface for iface in interfaces},
        "services": [
            Service.from_json(service_data)
            for service_data in json_data.get("services_local", [])
        ],
        "services_json": json_data.get("services_local", []),
        "source_json": json_data,
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
        data["board_id"] = details["board_id"]
    else:
        data["firmware_version"] = json_data["firmware_version"]
        data["firmware_manufacturer"] = json_data["firmware_mfg"]
        data["model"] = json_data["model"]
        data["board_id"] = json_data["board_id"]

    if "tunnels" in json_data:
        tunnels = json_data["tunnels"]
        data["active_tunnel_count"] = int(tunnels["active_tunnel_count"])
    else:
        data["active_tunnel_count"] = int(json_data["active_tunnel_count"])

    if link_info := json_data.get("link_info"):
        data["links"] = [
            LinkInfo.from_json(
                link_info, source=data["node_name"].lower(), ip_address=ip_address
            )
            for ip_address, link_info in link_info.items()
        ]

    return SystemInfo(**data)


@attr.s(auto_attribs=True)
class VersionChecker:
    """Compares versions to the configured most recent version.

    Methods return a number between -1 and 3, where 0 is current, -1 indicates a
    development version (or other parse error), and 3 is very far behind.

    """

    _firmware: tuple[int, ...]
    _api: tuple[int, ...]

    @classmethod
    def from_config(cls, config: AppConfig.Aredn) -> VersionChecker:
        api_version = tuple(int(value) for value in config.current_api.split("."))
        firmware_version = tuple(
            int(value) for value in config.current_firmware.split(".")
        )
        return cls(firmware_version, api_version)

    def firmware(self, version: str) -> int:
        """Check how current the firmware version is."""
        try:
            current = tuple(int(value) for value in version.split("."))
        except ValueError:
            return -1
        return _version_delta(current, self._firmware)

    def api(self, version: str) -> int:
        """Check how current the API version is."""
        try:
            current = tuple(int(value) for value in version.split("."))
        except ValueError:
            return -1
        return _version_delta(current, self._api)


def _version_delta(sample: tuple[int, ...], standard: tuple[int, ...]) -> int:
    """Weight the difference between two versions on a scale of 0 to 3."""
    length = max(len(standard), len(sample))
    for position, (current, goal) in enumerate(
        zip_longest(sample, standard, fillvalue=0), start=1
    ):
        delta = goal - current
        if delta < 0:
            logger.warning(
                "Current version out of date?",
                current=".".join(str(v) for v in standard),
                seen=".".join(str(v) for v in sample),
            )
        if delta == 0:
            continue
        elif position == 1:
            # major version is behind
            return 3
        elif position == length:
            # reached the final value
            if length == 2:
                # if there are only two parts then treat the lsat number more severely
                return 1 if delta < 2 else 2
            else:
                return 1 if delta < 4 else 2
        else:
            # some middle value
            return 2 if delta < 2 else 3

    return 0
