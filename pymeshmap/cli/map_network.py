"""Maps the network, storing the result in the database."""
from __future__ import annotations

import asyncio
import math
import sys
import time
from collections import defaultdict
from datetime import datetime
from operator import attrgetter
from typing import DefaultDict, Dict, List

import click
from loguru import logger
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models
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

    Looks for existing nodes by WiFi MAC address and name.

    *Attention:* This does not currently implement the "removed nodes" of
    MeshMap, the goal is to replace that functionality with a node status.

    """
    count: DefaultDict[str, int] = defaultdict(int)
    for node in nodes:
        count["total"] += 1
        # check to see if node exists in database by name, WiFi IP, or WiFi MAC address
        results: List[models.Node] = dbsession.query(models.Node).filter(
            or_(
                models.Node.wlan_ip == node.wifi_ip_address,
                models.Node.wlan_mac_address == node.wifi_mac_address,
                models.Node.name == node.node_name,
            )
        ).all()
        if len(results) > 1:
            count["issues"] += 1
            model: models.Node = fix_multiple_entries(dbsession, results)
        else:
            model = results[0]

        if model is None:
            # create new database model
            logger.debug("Saving {} to database", node)
            count["added"] += 1
            model = models.Node(
                wlan_ip=node.wifi_ip_address,
                name=node.node_name,
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
            model.wlan_ip = node.wifi_ip_address
            model.name = node.node_name
            model.last_seen = datetime.now()  # timezone?
            model.up_time = node.up_time
            model.load_average = node.load_averages
            model.model = node.model
            model.board_id = node.board_id
            model.firmware_version = node.firmware_version
            model.firmware_manufacturer = node.firmware_manufacturer
            model.api_version = node.api_version
            model.grid_square = node.grid_square
            model.wlan_mac_address = node.wifi_mac_address
            model.ssid = node.ssid
            model.channel = node.channel
            model.channel_bandwidth = node.channel_bandwidth
            model.services = node.services_json
            model.tunnel_installed = node.tunnel_installed
            model.active_tunnel_count = node.active_tunnel_count
            model.latitude = node.latitude
            model.longitude = node.longitude

    logger.success("Nodes written to database: {}", dict(count))
    return


def fix_multiple_entries(dbsession: Session, rows: List[models.Node]) -> models.Node:
    """Resolve multiple entries for a name, IP, and/or MAC address.

    Currently saves the most recently seen entry and deletes the rest.

    Returns the model to use.

    """

    matching_nodes = sorted(rows, key=attrgetter("last_seen"))

    logger.debug("Matching entries: {}", matching_nodes)
    if len(matching_nodes) > 2:
        logger.warning(
            "Found {} entries in DB based on name, IP and/or MAC", len(matching_nodes)
        )

    most_recent = matching_nodes.pop(-1)
    for model in matching_nodes:
        logger.debug("Deleting duplicate(?) entry: {}", model)
        dbsession.delete(model)

    return most_recent


def save_links(links: List[LinkInfo], dbsession: Session):
    """Saves link data to the database.

    This implements the bearing/distance functionality in Python
    rather than using SQL triggers,
    thus the MeshMap triggers will need to be deleted/disabled.

    """
    count: DefaultDict[str, int] = defaultdict(int)

    for link in links:
        count["total"] += 1
        source: models.Node = dbsession.query(models.Node).get(link.source)
        destination: models.Node = dbsession.query(models.Node).get(link.destination)
        model = models.Link(
            source_ip=source.wlan_ip, target_ip=destination.wlan_ip, olsr_cost=link.cost
        )

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
