"""Main command-line entry point for `meshinfo`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger
from pyramid.scripting import prepare

from meshinfo import VERSION, backup, collector, models, report, web
from meshinfo.aredn import VersionChecker
from meshinfo.config import AppConfig, configure
from meshinfo.historical import HistoricalStats
from meshinfo.poller import Poller


def main(argv: list = None):  # noqa: C901
    """Main CLI entry point for 'meshinfo'."""

    parser = build_parser()

    args = parser.parse_args(argv)
    if args.version:
        print(f"meshinfo version {VERSION}")
        return

    config = configure()
    settings = config.get_settings()
    app_config: AppConfig = settings["app_config"]

    if args.command == "web":
        # web process doesn't need to be "prepared"
        if args.bind:
            app_config.web.bind = args.bind
        if args.workers:
            app_config.web.workers = args.workers
        web.main(config, app_config.web)
        return

    env = prepare(registry=config.registry)
    request = env["request"]

    poller = request.find_service(Poller)
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

    ensure_directories(app_config)

    if args.command == "export":
        sys.exit(backup.export_data(app_config.data_dir, args.filename))

    if args.command == "import":
        sys.exit(backup.import_data(args.filename, app_config.data_dir))

    try:
        session_factory = models.get_session_factory(models.get_engine(app_config.db))
    except Exception as exc:
        logger.error(f"Failed to configure database connection: {exc!r}")
        sys.exit("Database configuration failed, review logs for details")

    if args.command == "collector":
        historical_stats: HistoricalStats = request.find_service(HistoricalStats)
        sys.exit(
            collector.main(
                app_config.local_node,
                session_factory,
                poller,
                historical_stats,
                config=app_config.collector,
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
        "--bind",
        help="server socket to bind to",
    )
    web_parser.add_argument(
        "--workers",
        type=int,
        help="number of worker processes",
    )

    # Export/backup
    export_parser = sub_parsers.add_parser(
        "export",
        help="export data files to tarball",
        description="Exports RRD files and data files to specified TGZ file.",
    )
    export_parser.add_argument(
        "filename",
        type=Path,
        help="Name of tarball to create",
    )

    # Import/restore
    import_parser = sub_parsers.add_parser(
        "import",
        help="import data files from tarball",
        description="Imports RRD files and data files from specified TGZ file.",
    )
    import_parser.add_argument(
        "filename",
        type=Path,
        help="Name of tarball to load",
    )
    return parser


def ensure_directories(app_config: AppConfig):
    """Ensure necessary directories exists."""

    for path in (app_config.data_dir, app_config.rrd_dir):
        if path.exists():
            continue
        try:
            path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            sys.exit(f"Failed to create directory: {path!s}")
