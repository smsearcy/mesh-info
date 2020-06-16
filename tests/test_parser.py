"""Test parsing of AREDN node data."""

import json
from pathlib import Path
from pprint import pprint

import pytest

from pymeshmap import parser


@pytest.fixture(scope="module")
def data_folder() -> Path:
    return Path(__file__).parent / "data"


@pytest.mark.parametrize(
    "filename", list(Path(__file__).parent.glob("data/sysinfo-*.json"))
)
def test_parse_all_sysinfo_examples(filename):
    with open(filename, "r") as f:
        json_data = json.load(f)
    system_info = parser.load_node_data(json_data)
    assert system_info is not None


@pytest.mark.parametrize(
    "filename, uptime",
    [("sysinfo-1_5.json", "0 days, 2:39:38"), ("sysinfo-1_7.json", "3 days, 19:44:05")],
)
def test_load_node_data(data_folder, filename, uptime):

    with open(data_folder / filename, "r") as f:
        json_data = json.load(f)

    pprint(json_data)

    system_info = parser.load_node_data(json_data)

    pprint(system_info)

    assert system_info.up_time == uptime
