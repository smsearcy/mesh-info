"""This process polls the network and displays the results to the user."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Callable, Dict

from loguru import logger

from .aredn import LinkInfo, SystemInfo, VersionChecker
from .poller import NetworkInfo, NodeError, OlsrData, PollingError
from .types import LinkType

VERBOSE_TO_LOGGING = {0: "SUCCESS", 1: "INFO", 2: "DEBUG", 3: "TRACE"}

# Define terminal colors for output
INFO = "\033[37m"  # white
NOTE = "\033[34m"  # blue
CRIT = "\033[31;1m"  # bright red
BAD = "\033[31m"  # red
WARN = "\033[33m"  # yellow
OK = "\033[32m"  # green
GOOD = "\033[32;1m"  # bright green
END = "\033[0m"
NOT_AVAILABLE = f"{WARN}Not Available{END}"

VERSION_COLOR = {
    0: OK,
    1: WARN,
    2: BAD,
    3: CRIT,
}


def main(
    local_node: str,
    poller: Callable,
    version_checker: VersionChecker,
    *,
    verbose: int = 0,
    save_errors: bool = False,
    output_path: Path = None,
):
    """Crawls network and prints information about the nodes and links.

    Detailed output is not printed until the crawler finishes.
    Increase amount of logging output by increasing `verbose` from 1 to 3.

    Does not use or require a database.

    Default hostname is "localnode.local.mesh".

    """

    output_path = output_path or Path(".")

    log_level = VERBOSE_TO_LOGGING.get(verbose, "SUCCESS")
    logger.remove()
    logger.add(sys.stderr, level=log_level)

    start_time = time.monotonic()

    async_debug = log_level == "DEBUG"
    try:
        nodes, links, errors = asyncio.run(
            network_info(local_node, poller), debug=async_debug
        )
    except RuntimeError as exc:
        return str(exc)

    for node in nodes:
        pprint_node(node, version_checker)

    for link in links:
        pprint_link(link)

    if len(nodes) > 0 and len(links) > 0:
        print(
            f"{OK}Gathered results for {len(nodes):,d} nodes "
            f"and {len(links):,d} links.{END}",
        )
    elif len(nodes) > 0 and len(links) == 0:
        print(
            f"{WARN}Gathered results for {len(nodes):,d} nodes but 0 links!\n"
            "Is your node connected to a mesh network?  "
            f"Please run with -v for more information and/or report the issue{END}",
        )

    if len(errors) > 0:
        handle_errors(errors, output_path, save=save_errors)

    total_time = time.monotonic() - start_time
    print(f"{NOTE}Network report took {total_time:.2f} seconds{END}")


async def network_info(node: str, poller: Callable) -> NetworkInfo:
    """Connect to the OLSR daemon on the local node and get the network information."""
    olsr = await OlsrData.connect(node)
    return await poller(olsr)


def pprint_node(node: SystemInfo, checker: VersionChecker):
    """Pretty print information about an AREDN node."""
    print(f"Name: {INFO}{node.node_name}{END}")
    print(f"WLAN IP: {INFO}{node.wlan_ip_address}{END}\tMAC: {node.wlan_mac_address}")
    print(f"Model: {node.model}")

    firmware_color = VERSION_COLOR.get(checker.firmware(node.firmware_version), WARN)
    print(
        f"Firmware: {firmware_color}{node.firmware_manufacturer} "
        f"{node.firmware_version}{END}"
    )
    print(f"LAN IP: {node.lan_ip_address}")
    if node.latitude and node.longitude:
        location = f"{OK}{node.latitude}, {node.longitude}{END}"
    elif node.grid_square:
        location = f"{NOTE}{node.grid_square}{END}"
    else:
        location = NOT_AVAILABLE
    print(f"Location: {location}")
    print(
        "Uptime:",
        f"{INFO}{node.up_time}{END}" if node.up_time else f"{WARN}Not Available{END}",
    )

    print(
        "Loads:",
        ", ".join(_colorize_load(load) for load in node.load_averages)
        if node.load_averages
        else NOT_AVAILABLE,
    )

    if node.status == "off":
        mesh_info = f"{BAD}off{END}\tSSID: {WARN}{node.ssid or 'Unknown'}{END}"
    else:
        mesh_info = f"{OK}on{END}\tSSID: {INFO}{node.ssid}{END}"
    print("MESH RF:", mesh_info)

    band_color = WARN if node.band == "Unknown" else INFO
    print(f"Channel: {node.channel}\tBand: {band_color}{node.band}{END}")
    api_color = VERSION_COLOR.get(checker.api(node.api_version), WARN)
    print(f"API Version: {api_color}{node.api_version}{END}")
    print(f"Tunnel Count: {node.active_tunnel_count}")
    print(f"Link Count: {node.link_count}")
    print()


def pprint_link(link: LinkInfo):
    """Pretty-print the link information"""
    if link.type == LinkType.UNKNOWN:
        if link.olsr_cost is None:
            print(
                f"{link.source} -> {link.destination} <Unknown> "
                f"olsr cost: {WARN}unknown{END}"
            )
            return
        if link.olsr_cost > 10:
            color = CRIT
        elif link.olsr_cost > 6:
            color = BAD
        elif link.olsr_cost > 4:
            color = WARN
        elif link.olsr_cost > 2:
            color = OK
        else:
            color = GOOD
        print(
            f"{link.source} -> {link.destination} <Unknown> "
            f"olsr cost: {color}{link.olsr_cost:.2f}{END}"
        )
        return

    if link.quality is None:
        print(
            f"{link.source} -> {link.destination} {INFO}<{link.type!s}>{END} "
            f"Quality: {WARN}unknown{END}"
        )
        return

    if link.quality >= 0.9:
        color = OK
    elif link.quality >= 0.8:
        color = WARN
    elif link.quality >= 0.7:
        color = BAD
    else:
        color = CRIT
    print(
        f"{link.source} -> {link.destination} {INFO}<{link.type!s}>{END} "
        f"Quality: {color}{link.quality * 100:.2f}%{END}"
    )
    return


def _colorize_load(value: float) -> str:
    if value > 1:
        color = BAD
    elif value > 0.5:
        color = WARN
    else:
        color = OK
    return f"{color}{value}{END}"


def handle_errors(errors: Dict[str, NodeError], output: Path, *, save: bool):
    """Report on the nodes that had errors."""

    print(f"{BAD}Encountered errors with {len(errors):,d} nodes{END}")
    if save:
        print("Saving responses for nodes with errors")
    else:
        print("Use the --save-errors option to save responses from nodes with errors")
    for ip_address, result in errors.items():
        # TODO: MeshMap did a reverse DNS lookup to get the node name
        print(f"{WARN}{ip_address}: {result.error!s}{END}")
        if save:
            if result.error == PollingError.PARSE_ERROR:
                filename = f"sysinfo-{ip_address}-error.json"
            elif result.error in (
                PollingError.HTTP_ERROR,
                PollingError.INVALID_RESPONSE,
            ):
                filename = f"{ip_address}-response.txt"
            else:
                filename = f"{ip_address}-error.txt"
            open(output / filename, "w").write(result.response)
