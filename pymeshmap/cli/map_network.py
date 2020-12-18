"""Maps the network, storing the result in the database."""
from __future__ import annotations

import asyncio
import math
import sys
import time
from collections import defaultdict
from datetime import datetime
from operator import attrgetter
from typing import DefaultDict, Dict, List, Optional

import click
from loguru import logger
from sqlalchemy.orm import Session

from .. import models
from ..models import Link, Node, NodeStatus
from ..poller import LinkInfo, Poller, SystemInfo
from . import VERBOSE_TO_LOGGING


@click.command()
@click.argument("hostname", default="")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase logging output by specifying -v up to -vvv",
)
@click.option(
    "--dryrun", "dry_run", is_flag=True, help="Do not commit changes to the database"
)
@click.pass_obj
def main(settings: Dict, hostname: str, verbose: int, dry_run: bool):
    """Map the network and store information in the database."""

    log_level = VERBOSE_TO_LOGGING.get(verbose, "SUCCESS")
    logger.remove()
    logger.add(sys.stderr, level=log_level)

    hostname = hostname or settings["pymeshmap.local_node"]

    try:
        session_factory = models.get_session_factory(models.get_engine(settings))
    except Exception as exc:
        logger.exception("Failed to connect to database")
        raise click.ClickException(f"Failed to connect to database: {exc!s}")

    start_time = time.monotonic()

    async_debug = log_level == "DEBUG"
    poller = Poller(
        hostname,
        read_timeout=settings["poller.read_timeout"],
        connect_timeout=settings["poller.connect_timeout"],
        total_timeout=settings["poller.total_timeout"],
        max_connections=settings["poller.max_connections"],
    )
    nodes, links, errors = asyncio.run(poller.network_info(), debug=async_debug)

    poller_finished = time.monotonic()
    poller_elapsed = poller_finished - start_time
    click.secho(f"Network polling took {poller_elapsed}s ({poller_elapsed / 60:.2f}m)")

    with models.session_scope(session_factory, dry_run) as dbsession:
        save_nodes(nodes, dbsession)
        save_links(links, dbsession)

    updates_finished = time.monotonic()
    updates_elapsed = updates_finished - poller_finished

    click.secho(
        f"Database updates took {updates_elapsed}s ({updates_elapsed / 60:.2f}m)"
    )

    total_elapsed = time.monotonic() - start_time
    click.secho(f"Total time: {total_elapsed}s ({total_elapsed / 60:.2f}m)")
    return


def save_nodes(nodes: List[SystemInfo], dbsession: Session):
    """Saves node information to the database.

    Looks for existing nodes by WLAN MAC address and name.

    """
    count: DefaultDict[str, int] = defaultdict(int)
    for node in nodes:
        count["total"] += 1
        # check to see if node exists in database by name and WLAN MAC address

        model = get_db_model(dbsession, node)

        if model is None:
            # create new database model
            logger.debug("Saving {} to database", node)
            count["added"] += 1
            model = Node(
                name=node.node_name,
                status=NodeStatus.ACTIVE,
                wlan_ip=node.wifi_ip_address,
                description=node.description,
                wlan_mac_address=node.wifi_mac_address,
                last_seen=datetime.now(),  # timezone?
                up_time=node.up_time,
                load_averages=node.load_averages,
                model=node.model,
                board_id=node.board_id,
                firmware_version=node.firmware_version,
                firmware_manufacturer=node.firmware_manufacturer,
                api_version=node.api_version,
                latitude=node.latitude,
                longitude=node.longitude,
                grid_square=node.grid_square,
                ssid=node.ssid,
                channel=node.channel,
                channel_bandwidth=node.channel_bandwidth,
                band=node.band,
                services=node.services_json,
                tunnel_installed=node.tunnel_installed,
                active_tunnel_count=node.active_tunnel_count,
                system_info=node.source_json,
            )
            dbsession.add(model)
        else:
            # update database model
            logger.debug("Updating {} in database with {}", model, node)
            count["updated"] += 1
            model.name = node.node_name
            model.status = NodeStatus.ACTIVE
            model.wlan_ip = node.wifi_ip_address
            model.description = node.description
            model.wlan_mac_address = node.wifi_mac_address
            model.last_seen = datetime.now()  # timezone?
            model.up_time = node.up_time
            model.load_averages = node.load_averages
            model.model = node.model
            model.board_id = node.board_id
            model.firmware_version = node.firmware_version
            model.firmware_manufacturer = node.firmware_manufacturer
            model.api_version = node.api_version
            model.latitude = node.latitude
            model.longitude = node.longitude
            model.grid_square = node.grid_square
            model.ssid = node.ssid
            model.channel = node.channel
            model.channel_bandwidth = node.channel_bandwidth
            model.services = node.services_json
            model.tunnel_installed = node.tunnel_installed
            model.active_tunnel_count = node.active_tunnel_count

    logger.success("Nodes written to database: {}", dict(count))
    return


def get_db_model(dbsession: Session, node: SystemInfo) -> Optional[Node]:
    """Get the best match database record for this node."""
    # Find the most recently seen node that matches both name and MAC address
    query = dbsession.query(Node).filter(
        Node.wlan_mac_address == node.wifi_mac_address,
        Node.name == node.node_name,
    )
    model = _get_most_recent(query.all())
    if model:
        return model

    # Find active node with same hardware
    query = dbsession.query(Node).filter(
        Node.wlan_mac_address == node.wifi_mac_address, Node.status == NodeStatus.ACTIVE
    )
    model = _get_most_recent(query.all())
    if model:
        return model

    # Find active node with same name
    query = dbsession.query(Node).filter(
        Node.name == node.node_name, Node.status == NodeStatus.ACTIVE
    )
    model = _get_most_recent(query.all())
    if model:
        return model

    # Nothing found, treat as a new node
    return None


def _get_most_recent(results: List[Node]) -> Optional[Node]:
    """Get the most recently seen node, optionally marking the others inactive."""
    if len(results) == 0:
        return None

    results = sorted(results, key=attrgetter("last_seen"), reverse=True)
    for model in results[1:]:
        if model.status == NodeStatus.ACTIVE:
            logger.debug("Marking older match inactive: {}", model)
            model.status = NodeStatus.INACTIVE

    return results[0]


def save_links(links: List[LinkInfo], dbsession: Session):
    """Saves link data to the database.

    This implements the bearing/distance functionality in Python
    rather than using SQL triggers,
    thus the MeshMap triggers will need to be deleted/disabled.

    """
    count: DefaultDict[str, int] = defaultdict(int)

    for link in links:
        count["total"] += 1
        source: Node = (
            dbsession.query(Node)
            .filter(Node.wlan_ip == link.source, Node.status == NodeStatus.ACTIVE)
            .one()
        )
        destination: Node = (
            dbsession.query(Node)
            .filter(Node.wlan_ip == link.destination, Node.status == NodeStatus.ACTIVE)
            .one()
        )
        model = Link(source=source, destination=destination, olsr_cost=link.cost)

        if (
            source.longitude is None
            or source.latitude is None
            or destination.longitude is None
            or destination.latitude is None
        ):
            count["missing location info"] += 1
            model.distance = None
            model.bearing = None
        else:
            count["location calculated"] += 1
            # calculate the bearing/distance
            model.distance = distance(
                source.latitude,
                source.longitude,
                destination.latitude,
                destination.longitude,
            )
            model.bearing = bearing(
                source.latitude,
                source.longitude,
                destination.latitude,
                destination.longitude,
            )

        dbsession.merge(model)

    logger.success("Links written to database: {}", dict(count))
    return


def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two points in kilometers via haversine."""
    # convert from degrees to radians
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    lon_delta = math.radians(lon2 - lon1)

    # 6371km is the (approximate) radius of Earth
    d = (
        2
        * 6371
        * math.asin(
            math.sqrt(
                hav(lat2 - lat1) + math.cos(lat1) * math.cos(lat2) * hav(lon_delta)
            )
        )
    )
    return round(d, 3)


def hav(theta: float) -> float:
    """Calculate the haversine of an angle."""
    return math.pow(math.sin(theta / 2), 2)


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the bearing between two coordinates."""
    # convert from degrees to radians
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    lon_delta = math.radians(lon2 - lon1)

    b = math.atan2(
        math.sin(lon_delta) * math.cos(lat2),
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(lon_delta),
    )

    return round(math.degrees(b), 1)
