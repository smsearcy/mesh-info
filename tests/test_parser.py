"""Test parsing of AREDN node data."""

import json
from pathlib import Path
import pytest

from pymeshmap import parser


@pytest.fixture(scope="module")
def data_folder() -> Path:
    return Path(__file__).parent / "data"


@pytest.mark.parametrize(
    "filename",
    list(Path(__file__).parent.glob("data/sysinfo-*.json")),
    ids=lambda obj: obj.name,
)
def test_parse_all_sysinfo_examples(filename):
    """Simply validate that all sample 'sysinfo.json' files parse without errors."""
    with open(filename, "r") as f:
        json_data = json.load(f)
    system_info = parser.load_node_data(json_data)
    assert system_info is not None


def test_api_version_1_0(data_folder):
    """Test parsing API version 1.0"""

    with open(data_folder / "sysinfo-1.0-sample.json", "r") as f:
        json_data = json.load(f)
    system_info = parser.load_node_data(json_data)

    # I could just construct a second object but I'm not checking everything
    assert system_info.node_name == "N0CALL-Oceanside-West"
    assert len(system_info.interfaces) == 5
    assert system_info.model == "Ubiquiti Rocket M"
    assert system_info.grid_square == ""
    assert system_info.latitude == -38.053394
    assert system_info.longitude == -6.193114
    assert system_info.ssid == "ArednMeshNetwork"
    assert system_info.channel == "-2"
    assert system_info.channel_bandwidth == "5"
    assert system_info.api_version == "1.0"


def test_api_version_1_5(data_folder):
    """Test parsing API version 1.5"""

    with open(data_folder / "sysinfo-1.5-sample.json", "r") as f:
        json_data = json.load(f)
    system_info = parser.load_node_data(json_data)

    # I could just construct a second object but I'm not checking everything
    assert system_info.node_name == "N0CALL-bm2-1"
    assert len(system_info.interfaces) == 4
    assert system_info.interfaces["eth0"].ip_address == "10.206.233.110"
    assert system_info.model == "Bullet M2 HP "
    assert system_info.grid_square == "DA05iv"
    assert system_info.latitude == -30.960324
    assert system_info.longitude == 73.324469
    assert system_info.ssid == "ArednMeshNetwork"
    assert system_info.channel == "-2"
    assert system_info.channel_bandwidth == "10"
    assert system_info.api_version == "1.5"
    assert len(system_info.load_averages) == 3
    assert system_info.up_time == "0 days, 2:39:38"
    assert system_info.active_tunnel_count == 0
    assert not system_info.tunnel_installed


def test_api_version_1_6(data_folder):
    """Test parsing API version 1.6"""

    with open(data_folder / "sysinfo-1.6-services.json", "r") as f:
        json_data = json.load(f)
    system_info = parser.load_node_data(json_data)

    # I could just construct a second object but I'm not checking everything
    assert system_info.node_name == "N0CALL-NSM2-3-East-Hills"
    assert system_info.description == "Elevation 1850' Pointing WSW"
    assert len(system_info.interfaces) == 11
    assert system_info.interfaces["eth0"].ip_address is None
    assert system_info.model == "NanoStation M2 "
    assert system_info.grid_square == "EH02ht"
    assert system_info.latitude == 54.894873
    assert system_info.longitude == 77.502536
    assert system_info.ssid == "ArednMeshNetwork"
    assert system_info.channel == "-2"
    assert system_info.channel_bandwidth == "10"
    assert system_info.api_version == "1.6"
    assert len(system_info.load_averages) == 3
    assert system_info.up_time == "255 days, 3:00:03"
    assert system_info.active_tunnel_count == 0
    assert not system_info.tunnel_installed
    assert len(system_info.services) == 1


def test_api_version_1_7(data_folder):
    """Test parsing API version 1.7"""

    with open(data_folder / "sysinfo-1.7-link_info.json", "r") as f:
        json_data = json.load(f)
    system_info = parser.load_node_data(json_data)

    # I could just construct a second object but I'm not checking everything
    assert system_info.node_name == "N0CALL-VC-RF-5G"
    assert len(system_info.interfaces) == 6
    assert system_info.interfaces["eth0"].ip_address is None
    assert system_info.model == "MikroTik RouterBOARD LHG 5HPnD-XL"
    assert system_info.grid_square == "AH58ku"
    assert system_info.latitude == -18.627378
    assert system_info.longitude == 56.804502
    assert system_info.ssid == "ArednMeshNetwork"
    assert system_info.channel == "177"
    assert system_info.channel_bandwidth == "20"
    assert system_info.api_version == "1.7"
    assert len(system_info.load_averages) == 3
    assert system_info.up_time == "3 days, 19:44:05"
    assert system_info.active_tunnel_count == 0
    assert not system_info.tunnel_installed
    assert len(system_info.link_info) == 2
