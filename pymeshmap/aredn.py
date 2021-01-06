"""Define data and functionality related to radios and AREDN software."""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

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
    services_json: List[Dict] = attr.ib()
    status: str = attr.ib()
    source_json: Dict = attr.ib()
    description: str = attr.ib(default="")
    frequency: str = attr.ib(default="")
    up_time: str = attr.ib(default="")
    load_averages: Optional[List[float]] = attr.ib(default=None)

    @property
    def lan_ip_address(self) -> str:
        iface_names = ["br-lan", "eth0", "eth0.0"]
        for iface in iface_names:
            if iface not in self.interfaces or not self.interfaces[iface].ip_address:
                continue
            return self.interfaces[iface].ip_address or ""
        return ""

    @property
    def wlan_interface(self) -> Optional[Interface]:
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
    def wlan_ip_address(self) -> str:
        return getattr(self.wlan_interface, "ip_address", "")

    @property
    def wlan_mac_address(self) -> str:
        return getattr(self.wlan_interface, "mac_address", "").replace(":", "").lower()

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
        return f"{self.node_name} ({self.wlan_ip_address})"


def load_system_info(json_data: Dict[str, Any]) -> SystemInfo:
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
        data["board_id"] = details["model"]
    else:
        data["firmware_version"] = json_data["firmware_version"]
        data["firmware_manufacturer"] = json_data["firmware_mfg"]
        data["model"] = json_data["model"]
        data["board_id"] = json_data["model"]

    if "tunnels" in json_data:
        tunnels = json_data["tunnels"]
        data["active_tunnel_count"] = int(tunnels["active_tunnel_count"])
        data["tunnel_installed"] = str(tunnels["tunnel_installed"]).lower() == "true"
    else:
        data["active_tunnel_count"] = int(json_data["active_tunnel_count"])
        data["tunnel_installed"] = str(json_data["tunnel_installed"]).lower() == "true"

    return SystemInfo(**data)
