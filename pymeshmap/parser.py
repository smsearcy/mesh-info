"""Parses JSON information from AREDN nodes into an object.

Defines "schema" classes modeling the information returned by `sysinfo.json` and
returns that information as the dataclass `SystemInfo`, so the primary function
that will actually be called in here is `load_node_data()`.

"""

from __future__ import annotations

import html
import typing as t

import attr
from loguru import logger


def load_node_data(json_data: t.Dict) -> t.Optional[SystemInfo]:
    """Convert data from `sysinfo.json` into a dataclass.

    If it cannot parse the information it returns `None`.  Extra/unknown fields in the
    source data are ignored.

    """
    try:
        system_info = SystemInfo.from_json(json_data)
    except Exception as e:
        # `logger.exception()` gives a lot more information, but will it be too much?
        logger.exception("Failed to parse sysinfo.json data: {!r}", e)
        return None

    return system_info


@attr.s(auto_attribs=True, slots=True)
class Interface:
    """Data class to represent the individual interfaces on a node."""

    mac_address: str
    name: str
    ip_address: t.Optional[str] = None

    @classmethod
    def from_json(cls, raw_data: t.Dict[str, str]) -> Interface:
        return cls(
            mac_address=raw_data["mac"],
            name=raw_data["name"],
            ip_address=raw_data.get("ip") if raw_data.get("ip") != "none" else None,
        )


@attr.s(auto_attribs=True, slots=True)
class Service:
    """Data class to represent the individual services on a node."""

    name: str
    protocol: str
    link: str

    @classmethod
    def from_json(cls, raw_data: t.Dict[str, str]) -> Service:
        return cls(
            name=raw_data["name"], protocol=raw_data["protocol"], link=raw_data["link"]
        )


@attr.s(auto_attribs=True, slots=True)
class SystemInfo:
    """Data class to represent the data from 'sysinfo.json'.

    This is independent of the database model because there are parsed values that might
    not be stored in database yet.  The polling script will have functionality to
    convert this dataclass into the SQLAlchemy database model.

    The network interfaces are represented by a dictionary, indexed by the interface
    name.

    """

    node_name: str
    api_version: str
    grid_square: str
    latitude: t.Optional[float]
    longitude: t.Optional[float]
    interfaces: t.Dict[str, Interface]
    ssid: str
    channel: str
    channel_bandwidth: str
    model: str
    board_id: str
    firmware_version: str
    firmware_manufacturer: str
    active_tunnel_count: int
    tunnel_installed: bool
    services: t.List[Service]
    description: str = ""
    status: t.Optional[str] = None
    frequency: t.Optional[str] = None
    up_time: t.Optional[str] = None
    load_averages: t.Optional[t.List[float]] = None

    @classmethod
    def from_json(cls, raw_data: t.Dict[str, t.Any]) -> SystemInfo:
        interfaces = [
            Interface.from_json(iface_data) for iface_data in raw_data["interfaces"]
        ]

        data = {
            "node_name": raw_data["node"],
            "api_version": raw_data["api_version"],
            "grid_square": raw_data["grid_square"],
            "latitude": float(raw_data["lat"]) if raw_data["lat"] else None,
            "longitude": float(raw_data["lon"]) if raw_data["lon"] else None,
            "interfaces": {iface.name: iface for iface in interfaces},
            "services": [
                Service.from_json(service_data)
                for service_data in raw_data.get("services_local", [])
            ],
        }

        if "sysinfo" in raw_data:
            data["up_time"] = raw_data["sysinfo"]["uptime"]
            data["load_averages"] = [
                float(load) for load in raw_data["sysinfo"]["loads"]
            ]

        if "meshrf" in raw_data:
            meshrf = raw_data["meshrf"]
            data["ssid"] = meshrf["ssid"]
            data["channel"] = meshrf["channel"]
            data["channel_bandwidth"] = meshrf["chanbw"]
            data["status"] = meshrf.get("status")
            data["frequency"] = meshrf.get("freq")
        else:
            data["ssid"] = raw_data["ssid"]
            data["channel"] = raw_data["channel"]
            data["channel_bandwidth"] = raw_data["chanbw"]

        if "node_details" in raw_data:
            details = raw_data["node_details"]
            data["description"] = html.unescape(details.get("description", ""))
            data["firmware_version"] = details["firmware_version"]
            data["firmware_manufacturer"] = details["firmware_mfg"]
            data["model"] = details["model"]
            data["board_id"] = details["model"]
        else:
            data["firmware_version"] = raw_data["firmware_version"]
            data["firmware_manufacturer"] = raw_data["firmware_mfg"]
            data["model"] = raw_data["model"]
            data["board_id"] = raw_data["model"]

        if "tunnels" in raw_data:
            tunnels = raw_data["tunnels"]
            data["active_tunnel_count"] = int(tunnels["active_tunnel_count"])
            data["tunnel_installed"] = bool(tunnels["tunnel_installed"])
        else:
            data["active_tunnel_count"] = int(raw_data["active_tunnel_count"])
            data["tunnel_installed"] = bool(raw_data["tunnel_installed"])

        return SystemInfo(**data)
