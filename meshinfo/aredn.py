"""Define data and functionality related to radios and AREDN software."""

from __future__ import annotations

import html
import re
import typing
from itertools import zip_longest
from typing import Any

import attrs
import structlog
from attrs.converters import optional

from .types import Band, LinkType

if typing.TYPE_CHECKING:
    from .config import AppConfig


logger = structlog.get_logger()


def _load_mac_address(value: str) -> str:
    return value.replace(":", "").lower()


def _load_float(value: str | None) -> float | None:
    if not value:
        return None
    return float(value)


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


@attrs.define
class Interface:
    """Data class to represent the individual interfaces on a node."""

    name: str
    mac_address: str = attrs.field(converter=optional(_load_mac_address))
    ip_address: str | None = None

    def __attrs_post_init__(self):
        if self.ip_address == "none":
            self.ip_address = None


@attrs.define
class LinkInfo:
    """Data class to represent the link information available from AREDN.

    Source and destination nodes are identified by name.

    """

    source: str = attrs.field(converter=lambda val: val.lower())
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


@attrs.define(kw_only=True)
class SystemInfo:
    """Data class to represent the node data from 'sysinfo.json'.

    Data that is directly retrieved from the node is stored in this class
    and "derived" data is then determined at runtime via property attributes
    (e.g. band information).

    The network interfaces are represented by a dictionary,
    indexed by the interface name.

    For string values, missing data is typically stored as an empty string,
    particularly if an empty string would not be a valid value (e.g. SSID).
    If there is a situation in which missing/unknown values need to be distinguished
    from empty strings then `None` would be appropriate.
    In a case like node description it is an optional value,
    so I see no need for "Unknown"/`None`.

    """

    node_name: str = attrs.field(converter=lambda val: val.lower())
    display_name: str
    api_version: str
    grid_square: str
    latitude: float | None = attrs.field(converter=_load_float, default=None)
    longitude: float | None = attrs.field(converter=_load_float, default=None)
    interfaces: dict[str, Interface]
    ssid: str
    channel: str
    channel_bandwidth: str
    model: str
    board_id: str
    firmware_version: str
    firmware_manufacturer: str
    active_tunnel_count: int
    services_json: list[dict] = attrs.field(factory=list)
    status: str
    source_json: dict
    description: str = ""
    frequency: str = ""
    up_time: str = ""
    load_averages: list[float] | None = None
    links: list[LinkInfo] = attrs.field(factory=list)
    link_count: int | None = None

    # these are convenience attributes
    primary_interface: Interface | None = attrs.field(init=False)
    ip_address: str = attrs.field(init=False, default="")
    mac_address: str = attrs.field(init=False, default="")

    def __attrs_post_init__(self) -> None:
        for iface_name in ("wlan0", "wlan1", "eth0.3975", "eth1.3975", "br-nomesh"):
            if not (iface := self.interfaces.get(iface_name)):
                continue
            if iface.ip_address:
                self.primary_interface = iface
                self.ip_address = iface.ip_address
                self.mac_address = iface.mac_address
                break
        else:
            logger.warning(
                "Unable to identify wireless interface", interfaces=self.interfaces
            )

    @property
    def lan_ip_address(self) -> str:
        for iface_name in ("br-lan", "eth0", "eth0.0"):
            if not (iface := self.interfaces.get(iface_name)):
                continue
            if iface.ip_address:
                return iface.ip_address
        return ""

    @property
    def band(self) -> Band:
        if self.status != "on":
            return Band.OFF
        if self.board_id in NINE_HUNDRED_MHZ_BOARDS:
            return Band.NINE_HUNDRED_MHZ
        if self.channel in TWO_GHZ_CHANNELS:
            return Band.TWO_GHZ
        if self.channel in THREE_GHZ_CHANNELS:
            return Band.THREE_GHZ
        if self.channel in FIVE_GHZ_CHANNELS:
            return Band.FIVE_GHZ
        return Band.UNKNOWN

    @property
    def up_time_seconds(self) -> int | None:
        """Convert uptime string to seconds."""
        if self.up_time == "":
            return None
        if not (match := re.match(r"^(\d+) days?, (\d+):(\d+)", self.up_time)):
            logger.warning("Failed to parse uptime string", value=self.up_time)
            return None

        days = int(match.group(1))
        hours = int(match.group(2))
        minutes = int(match.group(3))

        return 86_400 * days + 3_600 * hours + 60 * minutes

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
        return sum(
            1 for link in self.links if link.type in {LinkType.WIREGUARD, LinkType.TUN}
        )

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
        ip_address: IP address used to connect to this node
            (used in case we cannot identify the primary interface).

    Returns:
        Data class with information about the node.

    """
    api_version = tuple(int(part) for part in json_data["api_version"].split("."))
    if api_version >= (1, 5):
        node_info = _load_system_info(json_data)
    else:
        node_info = _load_legacy_system_info(json_data)

    # handle issue of failing to identify the main wireless interface
    if not node_info.ip_address:
        node_info.ip_address = ip_address
    return node_info


def _load_system_info(json_data: dict[str, Any]) -> SystemInfo:
    """Load "modern" `sysinfo.json` (aka API >= 1.5)."""
    rf_info = json_data["meshrf"]
    details = json_data["node_details"]
    link_info = json_data.get("link_info") or {}

    return SystemInfo(
        node_name=json_data["node"],
        display_name=json_data["node"],
        api_version=json_data["api_version"],
        grid_square=json_data.get("grid_square", ""),
        latitude=json_data.get("lat"),
        longitude=json_data.get("lon"),
        interfaces=_load_interfaces(json_data["interfaces"]),
        services_json=json_data.get("services_local", []),
        up_time=json_data["sysinfo"]["uptime"],
        load_averages=[float(load) for load in json_data["sysinfo"]["loads"]],
        status=rf_info.get("status", "on"),
        ssid=rf_info.get("ssid", ""),
        channel=rf_info.get("channel", ""),
        channel_bandwidth=rf_info.get("chanbw", ""),
        frequency=rf_info.get("freq", ""),
        description=html.unescape(details.get("description", "")),
        firmware_version=details["firmware_version"],
        firmware_manufacturer=details["firmware_mfg"],
        model=details["model"],
        board_id=details["board_id"],
        active_tunnel_count=int(json_data["tunnels"]["active_tunnel_count"]),
        links=[
            _load_link_info(
                link_info, source=json_data["node"], destination_ip=ip_address
            )
            for ip_address, link_info in link_info.items()
        ],
        source_json=json_data,
    )


def _load_legacy_system_info(json_data: dict[str, Any]) -> SystemInfo:
    """Load `sysinfo.json` in older format (API version < 1.5)."""
    node_info = SystemInfo(
        node_name=json_data["node"],
        display_name=json_data["node"],
        api_version=json_data["api_version"],
        grid_square=json_data.get("grid_square", ""),
        latitude=json_data.get("lat"),
        longitude=json_data.get("lon"),
        interfaces=_load_interfaces(json_data["interfaces"]),
        ssid=json_data["ssid"],
        channel=json_data["channel"],
        channel_bandwidth=json_data["chanbw"],
        status="on",
        source_json=json_data,
        firmware_version=json_data["firmware_version"],
        firmware_manufacturer=json_data["firmware_mfg"],
        model=json_data["model"],
        board_id=json_data["board_id"],
        active_tunnel_count=int(json_data["active_tunnel_count"]),
    )
    if sys_info := json_data.get("sysinfo"):
        node_info.up_time = sys_info["uptime"]
        node_info.load_averages = [float(load) for load in sys_info["loads"]]
    return node_info


@attrs.define
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
        if position == 1:
            # major version is behind
            return 3
        if position == length:
            # reached the final value
            if length == 2:
                # if there are only two parts then treat the lsat number more severely
                return 1 if delta < 2 else 2
            return 1 if delta < 4 else 2
        # some middle value
        return 2 if delta < 2 else 3

    return 0


def _load_interfaces(values: list[dict]) -> dict[str, Interface]:
    """Load list of JSON interfaces into dictionary of data classes."""
    interfaces = (
        Interface(
            name=obj["name"], mac_address=obj.get("mac", ""), ip_address=obj.get("ip")
        )
        for obj in values
    )
    return {iface.name: iface for iface in interfaces}


def _load_link_info(
    json_data: dict[str, Any], *, source: str, destination_ip: str
) -> LinkInfo:
    """Construct the `LinkInfo` dataclass from the AREDN JSON information.

    Needs the name of the source node and I passed in as well.

    Args:
        json_data: JSON link information from `sysinfo.json`
        source: Hostname of source node (no domain)
        destination_ip: IP address of link destination

    """
    # fix example of a DTD link that wasn't properly identified as such
    try:
        interface = json_data["olsrInterface"]
    except KeyError:
        # I suspect this is a Babel-only link with no OLSR data...
        interface = json_data["interface"]
    missing_dtd = json_data["linkType"] == "" and interface == "br-dtdlink"
    type_ = "DTD" if missing_dtd else json_data["linkType"]
    try:
        link_type = getattr(LinkType, type_)
    except AttributeError as exc:
        logger.warning("Unknown link type", error=str(exc))
        link_type = LinkType.UNKNOWN

    # ensure consistent node names
    node_name = json_data["hostname"].replace(".local.mesh", "").lstrip(".").lower()
    if (link_cost := json_data.get("linkCost")) is not None and link_cost > 99.99:
        link_cost = 99.99

    return LinkInfo(
        source=source,
        destination=node_name,
        destination_ip=destination_ip,
        type=link_type,
        interface=interface,
        # FIXME: need another way to get this information without OLSR
        # (look at LQM data)
        quality=json_data.get("linkQuality"),
        neighbor_quality=json_data.get("neighborLinkQuality"),
        signal=json_data.get("signal"),
        noise=json_data.get("noise"),
        tx_rate=json_data.get("tx_rate"),
        rx_rate=json_data.get("rx_rate"),
        olsr_cost=link_cost,
    )
