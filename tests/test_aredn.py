"""Test network crawling functionality."""

import json
from pathlib import Path

import pytest

from pymeshmap import aredn


@pytest.mark.parametrize(
    "filename",
    list(Path(__file__).parent.glob("data/sysinfo-*.json")),
    ids=lambda obj: obj.name,
)
def test_parse_all_sysinfo_examples(filename):
    """Simply validate that all sample 'sysinfo.json' files parse without errors."""
    with open(filename, "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)
    assert system_info is not None

    # Make sure we identified the wireless IP address
    assert system_info.wifi_ip_address != ""


def test_api_version_1_0(data_folder):
    """Test parsing API version 1.0"""

    with open(data_folder / "sysinfo-1.0-sample.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

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
    assert not system_info.tunnel_installed


def test_api_version_1_5(data_folder):
    """Test parsing API version 1.5"""

    with open(data_folder / "sysinfo-1.5-sample.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

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
    system_info = aredn.load_system_info(json_data)

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
    assert system_info.wifi_ip_address == "10.159.123.176"
    assert system_info.band == "2GHz"


def test_api_version_1_7(data_folder):
    """Test parsing API version 1.7"""

    with open(data_folder / "sysinfo-1.7-link_info.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

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
    assert system_info.wifi_ip_address == "10.106.204.11"
    assert system_info.band == "5GHz"


def test_tunnel_only_1_6(data_folder):
    """Load information from a "tunnel" node, no WiFi and mulitple tunnels."""

    with open(data_folder / "sysinfo-1.6-tunnel-only.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

    # I could just construct a second object but I'm not checking everything
    assert system_info.node_name == "N0CALL-6-HILO-HAP"
    assert len(system_info.interfaces) == 20
    assert system_info.interfaces["eth0"].ip_address == "192.168.0.50"
    assert system_info.status == "off"
    assert system_info.ssid == ""
    assert system_info.api_version == "1.6"
    assert len(system_info.load_averages) == 3
    assert system_info.tunnel_installed
    assert system_info.active_tunnel_count == 11
    assert system_info.wifi_ip_address == "10.154.255.82"
    assert system_info.lan_ip_address == "10.215.250.145"


def test_lan_interface_eth0_0(data_folder):
    """Validate that eth0.0 is recognized as a LAN IP address."""

    with open(data_folder / "sysinfo-1.5-no-location.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

    assert system_info.lan_ip_address == "10.66.236.21"
