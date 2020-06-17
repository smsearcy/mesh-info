"""Parsing information from AREDN nodes with the Marshmallow library.

Defines "schema" classes modeling the information returned by `sysinfo.json` and
returns that information as the dataclass `SystemInfo`, so the primary function
that will actually be called in here is `load_node_data()`.

"""

import typing as t
from ipaddress import IPv4Address

import attr
from loguru import logger
from marshmallow import EXCLUDE, Schema, fields, post_load, pre_load


@attr.s(auto_attribs=True, slots=True)
class Interface:
    """Data class to represent the individual interfaces on a node."""

    mac_address: str
    name: str
    ip_address: t.Optional[IPv4Address] = None


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
    latitude: str
    longitude: str
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
    status: t.Optional[str] = None
    frequency: t.Optional[str] = None
    up_time: t.Optional[str] = None
    load_averages: t.Optional[t.List[float]] = None


class InterfaceParser(Schema):
    """Marshmallow schema to load the information in the 'interfaces' list."""

    mac_address = fields.String(data_key="mac", required=True)
    name = fields.String(required=True)
    ip_address = fields.Function(
        deserialize=lambda obj: IPv4Address(obj), data_key="ip"
    )

    @pre_load
    def strip_none(self, in_data, **kwargs):
        # API 1.0 had "ip": "none" so we want to remove that
        return {key: value for key, value in in_data.items() if value != "none"}

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

    firmware_version = fields.String()
    firmware_manufacturer = fields.String(data_key="firmware_mfg")
    model = fields.String()
    board_id = fields.String()


class TunnelParser(Schema):
    """Marshmallow schema to load the 'tunnels' information."""

    active_tunnel_count = fields.Integer()
    tunnel_installed = fields.Boolean()


class SystemInfoParser(Schema):
    """Marshmallow schema to validate/load output of `sysinfo.json`.

    Based on samples from API versions 1.0, 1.5 & 1.7

    """

    node_name = fields.String(data_key="node", required=True)
    api_version = fields.String(required=True)
    grid_square = fields.String()
    latitude = fields.Float(data_key="lat")
    longitude = fields.Float(data_key="lon")
    interfaces = fields.List(fields.Nested(InterfaceParser))
    link_info = fields.Dict(missing=dict)
    # TODO: need to do further research on what this array looks like
    services = fields.Raw(data_key="services_local", missing=list)

    # Nested dictionaries that need to be flatted in newer versions
    meshrf = fields.Nested(MeshRfParser, missing=dict)
    node_details = fields.Nested(NodeDetailsParser, missing=dict)
    sysinfo = fields.Nested(SysInfoParser, missing=dict)
    tunnels = fields.Nested(TunnelParser, missing=dict)

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

        return SystemInfo(**data)


def load_node_data(json_data: t.Dict, *, log=None) -> t.Optional[SystemInfo]:
    """Convert data from `sysinfo.json` into a dataclass.

    If it cannot parse the information it returns `None`.  Extra/unknown fields in the
    source data are ignored.

    """
    log = log or logger

    try:
        system_info: SystemInfo = SystemInfoParser(unknown=EXCLUDE).load(json_data)
    except Exception as e:
        # `log.exception()` gives a lot more information, but will it be too much?
        log.error("Failed to parse sysinfo.json data: {!r}", e)
        return None

    return system_info
