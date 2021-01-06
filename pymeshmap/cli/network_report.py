"""This process polls the network and displays the results to the user."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import click
from loguru import logger

from ..config import AppConfig
from ..poller import LinkInfo, NodeError, Poller, SystemInfo
from . import VERBOSE_TO_LOGGING

# TODO: replace these with proper configuration
# (and in a general location)
API_VERSIONS = {"1.7": "bright_green", "1.6": "green", "1.5": "yellow", "1.3": "red"}


@click.command()
@click.argument("hostname", default="")
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
@click.pass_obj
def main(
    app_config: AppConfig, hostname: str, verbose: int, save_errors: bool, path: str
):
    """Crawls network and prints information about the nodes and links.

    Detailed output is not printed until the crawler finishes.
    Increase amount of logging output by passing '--verbose'.

    Does not use or require a database.

    Default hostname is "localnode.local.mesh".

    """

    app_config.poller.node = hostname or app_config.poller.node

    log_level = VERBOSE_TO_LOGGING.get(verbose, "SUCCESS")
    logger.remove()
    logger.add(sys.stderr, level=log_level)

    start_time = time.monotonic()

    output_path = Path(path)

    async_debug = log_level == "DEBUG"
    poller = Poller.from_config(app_config.poller)
    nodes, links, errors = asyncio.run(poller.network_info(), debug=async_debug)

    for node in nodes:
        pprint_node(node)

    for link in links:
        pprint_link(link)

    if len(nodes) > 0 and len(links) > 0:
        click.secho(
            f"Gathered results for {len(nodes):,d} nodes and {len(links):,d} links.",
            fg="green",
        )
    elif len(nodes) > 0 and len(links) == 0:
        click.secho(
            f"Gathered results for {len(nodes):,d} nodes but 0 links!\n"
            "This could be due to a timing issue querying OLSR.  "
            "Please run with -v for more information and/or report the issue",
            fg="yellow",
        )
    elif len(nodes) == 0 and len(links) > 0:
        click.secho(
            f"Gathered results for {len(links):,d} links but 0 nodes!\n"
            f"This could be due to a timing issue querying OLSR.  "
            "Please run with -v for more information and/or report the issue",
            fg="yellow",
        )
    else:
        click.secho(
            "Failed to gather any results!  Connection issue to local node?\n", fg="red"
        )
    if len(errors) > 0:
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
                if error == NodeError.PARSE_ERROR:
                    filename = f"sysinfo-{ip_address}-error.json"
                elif error in (NodeError.HTTP_ERROR, NodeError.INVALID_RESPONSE):
                    filename = f"{ip_address}-response.txt"
                else:
                    filename = f"{ip_address}-error.txt"
                open(output_path / filename, "w").write(response)

    total_time = time.monotonic() - start_time
    click.secho(f"Network report took {total_time:.2f} seconds", fg="blue")


def pprint_node(node: SystemInfo):
    """Pretty print information about an AREDN node."""
    click.echo("Name: ", nl=False)
    click.secho(node.node_name, fg="blue")
    click.echo("MAC: ", nl=False)
    if node.wlan_mac_address:
        click.secho(node.wlan_mac_address, fg="green")
    else:
        click.secho("No MAC address found!", fg="red")
    click.echo(f"Model: {node.model}")

    # TODO: add check for current firmware (and "Linux?")
    click.echo(f"Firmware: {node.firmware_manufacturer} {node.firmware_version}")
    click.echo(f"LAN IP: {node.lan_ip_address}\tWLAN IP: {node.wlan_ip_address}")
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
        click.secho(node.ssid or "Unknown", fg="red")
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


def pprint_link(link: LinkInfo):
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
        # is this a tunnel or direct link?
        click.echo(f"{link.cost:.3f}")
