"""Main command-line entry point for `pymeshmap`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger
from pyramid.paster import bootstrap

from pymeshmap import __version__, collector, models, report, web
from pymeshmap.aredn import VersionChecker
from pymeshmap.config import configure
from pymeshmap.historical import HistoricalStats


def main(argv: list = None):
    """Main CLI entry point for 'pymeshmap'."""

    parser = build_parser()

    args = parser.parse_args(argv)
    if args.version:
        print(f"pymeshmap version {__version__}")
        return

    if args.command == "web":
        # web process doesn't need to be bootstrapped
        config = configure()
        web.main(config, host=args.host, port=args.port, reload=args.reload)
        return

    pyramid_ini = str(Path(__file__).parents[1] / "pyramid.ini")
    with bootstrap(pyramid_ini) as env:
        settings = env["registry"].settings
        request = env["request"]

        poller = request.find_service(name="poller")
        version_checker: VersionChecker = request.find_service(VersionChecker)

        # Check the report command first since it doesn't require database or storage
        if args.command == "report":
            if not args.path.is_dir():
                parser.error("output path must be an existing directory")

            sys.exit(
                report.main(
                    args.hostname,
                    poller,
                    version_checker,
                    verbose=args.verbose,
                    save_errors=args.save_errors,
                    output_path=args.path,
                )
            )

        data_dir = settings["data_dir"]
        if not data_dir.exists():
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                sys.exit(f"Failed to create data directory: {data_dir!s}")

        try:
            session_factory = models.get_session_factory(models.get_engine(settings))
        except Exception as exc:
            logger.error(f"Failed to configure database connection: {exc!r}")
            sys.exit("Database configuration failed, review logs for details")

        if args.command == "collector":
            historical_stats: HistoricalStats = request.find_service(HistoricalStats)
            sys.exit(
                collector.main(
                    settings["local_node"],
                    session_factory,
                    poller,
                    historical_stats,
                    config=settings["collector"],
                    run_once=args.run_once,
                )
            )

    sys.exit(f"command not recognized: {args.command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="map an AREDN mesh network")
    parser.add_argument(
        "--version", action="store_true", help="display version and exit"
    )
    sub_parsers = parser.add_subparsers(title="commands", dest="command")

    # Network Report Command
    report_parser = sub_parsers.add_parser(
        "report",
        help="report on current state of network",
        description="Polls network and displays information about the nodes and "
        "links. Does not require or use database.",
    )
    report_parser.add_argument(
        "hostname",
        nargs="?",
        default="localnode.local.mesh",
        help="node to connect to (defaults to 'localnode.local.mesh')",
    )
    report_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase logging output by specifying",
    )
    report_parser.add_argument(
        "--save-errors", action="store_true", help="save responses that cause error"
    )
    report_parser.add_argument(
        "--path", type=Path, default=".", help="path to save files to"
    )

    # Network Collector
    collector_parser = sub_parsers.add_parser(
        "collector",
        help="collect network information and store to database",
        description="Polls the network and stores the information to the database",
    )
    collector_parser.add_argument(
        "--run-once", action="store_true", help="collect information once then quit"
    )

    # Web Service
    web_parser = sub_parsers.add_parser(
        "web",
        help="run web service",
        description="Run web service",
    )
    web_parser.add_argument(
        "--host",
        help="ip address to listen on (defaults to 127.0.0.1)",
    )
    web_parser.add_argument(
        "--port",
        help="port to listen on (defaults to 6543)",
    )
    web_parser.add_argument(
        "--reload",
        action="store_true",
        help="automatically reload when source changes",
    )

    return parser
