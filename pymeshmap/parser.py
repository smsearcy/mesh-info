"""Parsing information from AREDN nodes with the Marshmallow library.

Defines "schema" classes modeling the information returned by `sysinfo.json` and
returns that information as the dataclass `SystemInfo`, so the primary function
that will actually be called in here is `load_node_data()`.

"""

from __future__ import annotations

import html
import typing as t
from ipaddress import IPv4Address

import attr
from loguru import logger
from marshmallow import EXCLUDE, Schema, fields, post_load


def load_node_data(json_data: t.Dict) -> t.Optional[SystemInfo]:
    """Convert data from `sysinfo.json` into a dataclass.

    If it cannot parse the information it returns `None`.  Extra/unknown fields in the
    source data are ignored.

    """
    try:
        system_info: SystemInfo = SystemInfoParser(unknown=EXCLUDE).load(json_data)
    except Exception as e:
        # `logger.exception()` gives a lot more information, but will it be too much?
        logger.error("Failed to parse sysinfo.json data: {!r}", e)
        return None

    return system_info


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
    link_info: t.Dict
    services: t.List
    description: str = ""
    status: t.Optional[str] = None
    frequency: t.Optional[str] = None
    up_time: t.Optional[str] = None
    load_averages: t.Optional[t.List[float]] = None


@attr.s(auto_attribs=True, slots=True)
class Interface:
    """Data class to represent the individual interfaces on a node."""

    mac_address: str
    name: str
    ip_address: t.Optional[IPv4Address] = None


class InterfaceParser(Schema):
    """Marshmallow schema to load the information in the 'interfaces' list."""

    mac_address = fields.String(data_key="mac", required=True)
    name = fields.String(required=True)
    ip_address = fields.Method(deserialize="load_ip_address", data_key="ip")

    def load_ip_address(self, value):
        # API 1.0 had "ip": "none" so we want to drop that
        if value == "none":
            return None
        return IPv4Address(value)

    @post_load
    def to_object(self, data, **kwargs):
        return Interface(**data)


class SysInfoParser(Schema):
    """Marshmallow schema to load the 'sysinfo' information."""

    up_time = fields.String(data_key="uptime")
    load_averages = fields.List(fields.Float, data_key="loads")


class MeshRfParser(Schema):
    """Marshmallow schema to load the 'meshrf' information."""

    ssid = fields.String(required=True)
    channel = fields.String()
    channel_bandwidth = fields.String(data_key="chanbw")
    status = fields.String()
    frequency = fields.String(data_key="freq")


class NodeDetailsParser(Schema):
    """Marshmallow schema to load the 'node_details' information."""

    description = fields.String()
    firmware_version = fields.String()
    firmware_manufacturer = fields.String(data_key="firmware_mfg")
    model = fields.String()
    board_id = fields.String()


class TunnelParser(Schema):
    """Marshmallow schema to load the 'tunnels' information."""

    active_tunnel_count = fields.Integer()
    tunnel_installed = fields.Boolean()


class ServicesParser(Schema):
    """Marshmallow schema to load the 'services' information."""

    # TODO: create data class?

    name = fields.String()
    protocol = fields.String()
    link = fields.String()


class SystemInfoParser(Schema):
    """Marshmallow schema to validate/load output of `sysinfo.json`.

    Based on samples from API versions 1.0, 1.5 & 1.7

    """

    node_name = fields.String(data_key="node", required=True)
    api_version = fields.String(required=True)
    grid_square = fields.String()
    latitude = fields.Method(deserialize="load_coordinate", data_key="lat")
    longitude = fields.Method(deserialize="load_coordinate", data_key="lon")
    interfaces = fields.List(fields.Nested(InterfaceParser))
    link_info = fields.Dict(missing=dict)
    services = fields.List(
        fields.Nested(ServicesParser, unknown=EXCLUDE),
        data_key="services_local",
        missing=list,
    )

    # Nested dictionaries that need to be flatted in newer versions
    meshrf = fields.Nested(MeshRfParser, missing=dict, unknown=EXCLUDE)
    node_details = fields.Nested(NodeDetailsParser, missing=dict, unknown=EXCLUDE)
    sysinfo = fields.Nested(SysInfoParser, missing=dict, unknown=EXCLUDE)
    tunnels = fields.Nested(TunnelParser, missing=dict, unknown=EXCLUDE)

    # Older APIs had some fields at the root level
    # (`to_object()` will overwrite these blank values with the above nested values)
    ssid = fields.String()
    channel = fields.String()
    channel_bandwidth = fields.String(data_key="chanbw")
    model = fields.String()
    board_id = fields.String()
    firmware_version = fields.String()
    firmware_manufacturer = fields.String(data_key="firmware_mfg")
    active_tunnel_count = fields.Integer()
    tunnel_installed = fields.Boolean()

    def load_coordinate(self, value):
        """Parse latitude/longitude values.

        Cannot use `mashmallow.fields.Float` because that chokes on an empty string.

        """
        if not value:
            return None
        return float(value)

    @post_load
    def to_object(self, data: t.Dict, **kwargs):
        """Create the `SystemInfo` dataclass from the parsed information.

        Because some values are nested in dictionaries in the newer firmware we need
        to "flatten" those out by copying those values (if set) into the main
        dictionary.

        This method is automatically called by Marshmallow when we call
        `SystemInfoParser.load()`.

        """

        # break out the nested dictionaries, but only update with known values
        keys_to_flatten = ["node_details", "meshrf", "sysinfo", "tunnels"]

        for key in keys_to_flatten:
            nested_dict = data.pop(key)
            data.update(
                {key: value for key, value in nested_dict.items() if value is not None}
            )

        # convert interfaces from list to dictionary indexed by interface name
        data["interfaces"] = {
            interface.name: interface for interface in data["interfaces"]
        }
        if "description" in data:
            # found an example where description had HTML entities
            data["description"] = html.unescape(data["description"])

        return SystemInfo(**data)
