"""Smoke tests for the CLI commands."""

from pymeshmap import cli


def test_collector_cli(mocker):
    mock = mocker.patch("pymeshmap.collector.main")
    mocker.patch("sys.exit")

    cli.main(["collector"])
    mock.assert_called_once()


def test_report_cli(mocker):
    mock = mocker.patch("pymeshmap.report.main")
    mocker.patch("sys.exit")

    cli.main(["report"])
    mock.assert_called_once()


def test_scrub_cli(mocker, tmp_path):
    mock = mocker.patch("pymeshmap.scrub.main")
    mocker.patch("sys.exit")

    source = tmp_path / "test.json"
    source.touch()
    output = tmp_path / "output.json"

    cli.main(["scrub", str(source), str(output)])
    mock.assert_called_once()
