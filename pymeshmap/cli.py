"""Main command-line entry point for `pymeshmap`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pymeshmap import __version__, collector, config, report, scrub, web


def main(argv: list = None):
    """Main CLI entry point for 'pymeshmap'."""

    parser = build_parser()

    args = parser.parse_args(argv)
    if args.version:
        print(f"pymeshmap version {__version__}")
        return

    app_config = config.app_config

    if args.command == "collector":
        result = collector.main(app_config, run_once=args.run_once)
    elif args.command == "report":
        if not args.path.is_dir():
            parser.error("output path must be an existing directory")
        result = report.main(
            app_config,
            args.hostname,
            verbose=args.verbose,
            save_errors=args.save_errors,
            output_path=args.path,
        )
    elif args.command == "scrub":
        result = scrub.main(args.filename, args.output)
    elif args.command == "web":
        result = web.main(
            app_config, host=args.host, port=args.port, reload=args.reload
        )
    else:
        result = "no command specified"

    sys.exit(result)


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

    # Scrub Sample Files
    scrub_parser = sub_parsers.add_parser(
        "scrub",
        help="scrub sensitive information from json sample files",
        description="Scrub sensitive data from 'sysinfo.json' files for testing",
    )
    scrub_parser.add_argument(
        "filename",
        type=argparse.FileType("r"),
        help="source file to scrub",
    )
    scrub_parser.add_argument(
        "output",
        type=argparse.FileType("w"),
        help="output file to write to",
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
