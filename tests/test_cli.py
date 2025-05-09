"""Smoke tests for the CLI commands."""

from __future__ import annotations

from meshinfo import cli
from meshinfo.config import from_env

app_config = from_env()


def test_collector_cli(mocker):
    mock = mocker.patch("meshinfo.collector.main")
    mocker.patch("sys.exit")

    cli.main(["collector"])
    mock.assert_called_once()


def test_collector_cli_run_once(mocker):
    mock = mocker.patch("meshinfo.collector.main")
    mocker.patch("sys.exit")

    cli.main(["collector", "--run-once"])
    mock.assert_called_once()


def test_report_cli(mocker):
    mock = mocker.patch("meshinfo.report.main")
    mocker.patch("sys.exit")

    cli.main(["report"])
    mock.assert_called_once()
