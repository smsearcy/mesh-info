"""Main command-line entry point for `pymeshmap`."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import random
import re
import string
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import click
from faker import Faker  # type: ignore
from loguru import logger

from pymeshmap import crawler

VERBOSE_TO_LOGGING = {0: "SUCCESS", 1: "INFO", 2: "DEBUG", 3: "TRACE"}


# TODO: replace these with proper configuration
LOCAL_NODE_NAME = "localnode.local.mesh"
CURRENT_STABLE_FIRMWARE = "3.20.3.0"
API_VERSIONS = {"1.7": "bright_green", "1.6": "green", "1.5": "yellow", "1.3": "red"}


@click.group()
@click.pass_context
def main(ctx):
    # TODO: configure environment
    ctx.obj = None
    return


@main.command()
@click.argument("hostname", default="localnode.local.mesh")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase logging output by specifying -v up to -vvv",
)
@click.option(
    "--save-errors",
    is_flag=True,
    help="Saves node responses that caused errors to the current directory",
)
@click.option(
    "--path",
    type=click.Path(file_okay=False, exists=True),
    default=".",
    help="Path to save files to",
)
def network_report(hostname: str, verbose: int, save_errors: bool, path: str):
    """Crawls network and prints information about the nodes and links.

    Detailed output is not printed until the crawler finishes.
    Increase amount of logging output by passing '--verbose'.

    Does not use or require a database.

    Default hostname is "localnode.local.mesh".

    """

    log_level = VERBOSE_TO_LOGGING.get(verbose, "SUCCESS")
    logger.remove()
    logger.add(sys.stderr, level=log_level)

    start_time = time.monotonic()

    output_path = Path(path)

    async_debug = log_level == "DEBUG"
    nodes, links, errors = asyncio.run(
        crawler.network_info(hostname), debug=async_debug
    )

    click.secho(f"Successfully gathered results for {len(nodes):,d} nodes", fg="blue")
    for node in nodes:
        pprint_node(node)

    for link in links:
        pprint_link(link)

    if len(errors) == 0:
        click.secho("No errors!", fg="green")
    else:
        click.secho(f"Encountered errors with {len(errors):,d} nodes", fg="red")
        if save_errors:
            click.echo("Saving responses for nodes with errors")
        else:
            click.echo(
                "Use the --save-errors option to save responses from nodes with errors"
            )
        for ip_address, (error, response) in errors.items():
            # TODO: MeshMap did a reverse DNS lookup to get the node name
            click.secho(f"{ip_address}: {error!s}", fg="yellow")
            if save_errors:
                open(output_path / f"{ip_address}-response.txt", "w").write(response)

    total_time = time.monotonic() - start_time
    click.secho(f"Network report took {total_time:.2f} seconds", fg="blue")


def pprint_node(node: crawler.SystemInfo):
    """Pretty print information about an AREDN node."""
    click.echo("Name: ", nl=False)
    click.secho(node.node_name, fg="blue")
    click.echo("MAC: ", nl=False)
    if node.wifi_mac_address:
        click.secho(node.wifi_mac_address, fg="green")
    else:
        click.secho("No MAC address found!", fg="red")
    click.echo(f"Model: {node.model}")

    # TODO: add check for current firmware (and "Linux?")
    click.echo(f"Firmware: {node.firmware_manufacturer} {node.firmware_version}")
    click.echo(f"LAN IP: {node.lan_ip_address}\tWAN IP: {node.wifi_ip_address}")
    click.echo("Location: ", nl=False)
    if node.latitude and node.longitude:
        click.secho(f"{node.latitude}, {node.longitude}", fg="green")
    elif node.grid_square:
        click.secho(node.grid_square, fg="yellow")
    else:
        click.secho("Not Available", fg="yellow")
    click.echo("Uptime: ", nl=False)
    if node.up_time:
        click.secho(node.up_time, fg="green")
    else:
        click.secho("Not Available", fg="yellow")
    click.echo("Loads: ", nl=False)

    def colorize_load(value: float) -> str:
        if value > 1:
            return "red"
        elif value > 0.5:
            return "yellow"
        else:
            return "green"

    if node.load_averages:
        load_colors = [colorize_load(load) for load in node.load_averages]
        click.secho(str(node.load_averages[0]), nl=False, fg=load_colors[0])
        click.echo(", ", nl=False)
        click.secho(str(node.load_averages[1]), nl=False, fg=load_colors[1])
        click.echo(", ", nl=False)
        click.secho(str(node.load_averages[2]), fg=load_colors[2])
    else:
        click.secho("Not Available", fg="yellow")
    click.echo("MESH RF: ", nl=False)
    if node.status == "off":
        click.secho("off", nl=False, fg="red")
        click.echo("\tSSID: ", nl=False)
        click.secho(node.ssid, fg="red")
    else:
        click.secho("on", nl=False, fg="green")
        click.echo("\tSSID: ", nl=False)
        click.secho(node.ssid, fg="green")
    click.echo(f"Channel: {node.channel}\tBand: ", nl=False)
    # good use for walrus operator (:=) if require Python 3.8
    # (or just make it a cached property)
    band = node.band
    if band != "Unknown":
        click.echo(band)
    else:
        click.secho(band, fg="yellow")
    click.echo("API Version: ", nl=False)
    click.secho(node.api_version, fg=API_VERSIONS.get(node.api_version, "bright_red"))
    click.echo(f"Tunnels: {node.tunnel_installed}\tCount: {node.active_tunnel_count}")
    click.echo()


def pprint_link(link: crawler.LinkInfo):
    click.echo(f"{link.source} -> {link.destination} cost: ", nl=False)
    if link.cost > 10:
        click.secho(f"{link.cost:.3f}", fg="bright_red", bold=True)
    elif link.cost > 6:
        click.secho(f"{link.cost:.3f}", fg="red")
    elif link.cost > 4:
        click.secho(f"{link.cost:.3f}", fg="bright_yellow", bold=True)
    elif link.cost > 2:
        click.secho(f"{link.cost:.3f}", fg="green")
    elif link.cost > 0.1:
        click.secho(f"{link.cost:.3f}", fg="bright_green", bold=True)
    else:
        # is this a tunnel?
        click.echo(f"{link.cost:.3f}")


@main.command(help="Scrub identifiable information from data files for testing.")
@click.argument("filename", type=click.File("r"))
@click.argument("output", type=click.File("w"))
def scrub_file(filename, output):
    """Scrub JSON files before adding to repository for tests."""

    sys_info = json.load(filename)
    # I'm assuming we always start with a dictionary
    scrubbed_info = _scrub_dict(sys_info)
    json.dump(scrubbed_info, output, indent=2)


def _scrub_unknown(key: str, value: Any) -> Any:
    if isinstance(value, dict):
        return _scrub_dict(value)
    elif isinstance(value, list):
        return _scrub_list(key, value)
    else:
        return _scrub_scalar(key, value)


def _scrub_dict(values: Dict[str, Any]) -> Dict:
    scrubbed_dict = {key: _scrub_unknown(key, value) for key, value in values.items()}
    return scrubbed_dict


def _scrub_list(key: str, values: List) -> List:
    scrubbed_list = [_scrub_unknown(key, value) for value in values]
    return scrubbed_list


def _scrub_scalar(key: str, value: Any) -> Any:
    if not key:
        logger.warning("Cannot scalar value without a key: {!r}", value)
        return value

    new_value = None
    fake = Faker()

    if key == "ip":
        # version 1.0 has "none" as an IP address, so may sure it is valid first
        try:
            ipaddress.ip_address(value)
        except ValueError:
            pass
        else:
            new_value = fake.ipv4_private(address_class="a")
    elif key == "lat" and value != "":
        new_value = f"{fake.latitude():.6f}"
    elif key == "lon" and value != "":
        new_value = f"{fake.longitude():.6f}"
    elif key == "mac" and value != "00:00:00:00":
        new_value = fake.mac_address().upper()
    elif key in ("node", "hostname", "name", "link"):
        new_value = re.sub(r"\d?[a-zA-Z]{1,2}\d{1,4}[a-zA-Z]{1,4}", "N0CALL", value)
    elif key == "grid_square" and value != "":
        new_value = random_grid_square()
    elif key == "ssid":
        new_value = "ArednMeshNetwork"

    if new_value is not None and new_value != value:
        print(f"Rewrote {value!r} to {new_value!r}")
        return new_value

    return value


def random_grid_square():
    """Generate a random MaidenHead grid square value."""
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    values = [
        random.randint(0, 17),
        random.randint(0, 17),
        random.randint(0, 9),
        random.randint(0, 9),
        random.randint(0, 24),
        random.randint(0, 24),
    ]
    grid_square = (
        uppercase[values[0]]
        + uppercase[values[1]]
        + f"{values[2]}{values[3]}"
        + lowercase[values[4]]
        + lowercase[values[5]]
    )
    return grid_square
