"""Parsing information from AREDN nodes.

The structure of the data classes is biased towards the organization of the data at the
time this was written.  We'll see how well that holds up over time.

"""

import typing as t

import attr
from loguru import logger
from marshmallow import EXCLUDE, Schema, fields, post_load, pre_load


@attr.s(auto_attribs=True, slots=True)
class Interface:
    mac_address: str
    name: str
    ip_address: str = None


@attr.s(auto_attribs=True, slots=True)
class SystemInfo:
    """Data object to represent the data from 'sysinfo.json'.

    This is independent of the database model because there are parse values that might
    not be stored in database yet.

    """

    node_name: str
    api_version: str
    grid_square: str
    latitude: str
    longitude: str
    interfaces: t.List[Interface]
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
    status: str = None
    frequency: str = None
    up_time: str = None
    load_averages: t.List[float] = None


class InterfaceParser(Schema):
    """Marshmallow schema to validate/load interface information."""

    mac_address = fields.String(data_key="mac", required=True)
    name = fields.String(required=True)
    ip_address = fields.String(data_key="ip")

    @pre_load
    def strip_none(self, in_data, **kwargs):
        # API 1.0 had "ip": "none" so we want to remove that
        return {key: value for key, value in in_data.items() if value != "none"}

    @post_load
    def to_object(self, data, **kwargs):
        return Interface(**data)


class SysInfoParser(Schema):
    up_time = fields.String(data_key="uptime")
    load_averages = fields.List(fields.Float, data_key="loads")


class MeshRfParser(Schema):
    ssid = fields.String(required=True)
    channel = fields.String()
    channel_bandwidth = fields.String(data_key="chanbw")
    status = fields.String()
    frequency = fields.String(data_key="freq")


class NodeDetailsParser(Schema):
    firmware_version = fields.String()
    firmware_manufacturer = fields.String(data_key="firmware_mfg")
    model = fields.String()
    board_id = fields.String()


class TunnelParser(Schema):
    active_tunnel_count = fields.Integer()
    tunnel_installed = fields.Boolean()


class SystemInfoParser(Schema):
    """Marshmallow schema to validate/load output of `sysinfo.json`.

    Based on samples from API versions 1.5 & 1.7

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

        # break out the nested dictionaries, but only update with known values
        keys_to_flatten = ["node_details", "meshrf", "sysinfo", "tunnels"]

        for key in keys_to_flatten:
            nested_dict = data.pop(key)
            data.update(
                {key: value for key, value in nested_dict.items() if value is not None}
            )

        return SystemInfo(**data)


def load_node_data(json_data: t.Dict, *, log=None) -> t.Optional[SystemInfo]:
    """Read data from `sysinfo.json` and return data for the database."""
    log = log or logger

    # This could get more tricky in the future with if I have to support
    # different parsers.  That's why more logic should go in `SysInfoParser.to_object()`
    # so we only need one parser, it just tries to find the information in the different
    # places
    try:
        system_info: SystemInfo = SystemInfoParser(unknown=EXCLUDE).load(json_data)
    except Exception as e:
        # `log.exception()` gives a lot more information, but will it be too much?
        log.error("Failed to parse sysinfo.json data: {!r}", e)
        return None

    return system_info
