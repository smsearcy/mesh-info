"""Main command-line entry point for `pymeshmap`."""

from __future__ import annotations

import click

from pymeshmap import config
from pymeshmap.cli import map_network, network_report, scrub


@click.group()
@click.pass_context
def main(ctx):
    settings = config.get_settings()
    ctx.obj = settings
    return


main.add_command(map_network.main, "map-network")
main.add_command(network_report.main, "network-report")
main.add_command(scrub.main, "scrub-file")
