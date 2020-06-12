"""Parsing information from AREDN nodes."""

import dataclasses
import typing as t

from loguru import logger
from marshmallow import Schema, fields, post_load


@dataclasses.dataclass
class Interface:
    mac_address: str
    name: str
    ip_address: str = None


@dataclasses.dataclass
class SystemInfo:
    """Data object to represent the data from 'sysinfo.json'.

    This is independent of the database model because there are parse values that might
    not be stored in database yet.

    """

    node: str
    node_details: t.Dict
    mesh_status: bool
    api_version: str
    sys_info: t.Dict
    grid_square: str
    latitude: str
    longitude: str
    interfaces: t.List[Interface]
    mesh_info: t.Dict
    tunnels: t.Dict
    link_info: t.Dict
    services: t.List
    up_time: str
    load_averages: t.List[float] = None


class InterfaceParser(Schema):
    """Marshmallow schema to validate/load interface information."""

    mac_address = fields.String(data_key="mac", required=True)
    name = fields.String(required=True)
    ip_address = fields.String(data_key="ip")

    @post_load
    def to_object(self, data, **kwargs):
        return Interface(**data)


class SysInfoParser(Schema):
    """Marshmallow schema to validate/load output of `sysinfo.json`.

    Based on samples from API versions 1.5 & 1.7

    """

    node = fields.String(required=True)
    node_details = fields.Dict(required=True)
    api_version = fields.String(required=True)
    sys_info = fields.Dict(data_key="sysinfo", required=True)
    grid_square = fields.String()
    latitude = fields.Float(data_key="lat")
    longitude = fields.Float(data_key="lon")
    interfaces = fields.List(fields.Nested(InterfaceParser))
    mesh_info = fields.Dict(data_key="meshrf", required=True)
    tunnels = fields.Dict(missing=dict)
    link_info = fields.Dict(missing=dict)
    # TODO: need to do further research on what this array looks like
    services = fields.Raw(data_key="services_local", missing=list)

    @post_load
    def to_object(self, data, **kwargs):
        # FIXME: put more logic instead of in dataclass's properties to map attributes
        return SystemInfo(**data)


def load_node_data(json_data: t.Dict, *, log=None) -> t.Optional[SystemInfo]:
    """Read data from `sysinfo.json` and return data for the database."""
    log = log or logger

    # This could get more tricky in the future with if I have to support
    # different parsers.  That's why more logic should go in `SysInfoParser.to_object()`
    # so we only need one parser, it just tries to find the information in the different
    # places
    try:
        system_info: SystemInfo = SysInfoParser().load(json_data)
    except Exception as e:
        # `log.exception()` gives a lot more information, but will it be too much?
        log.error("Failed to parse sysinfo data: {!r}", e)
        return None

    return system_info
