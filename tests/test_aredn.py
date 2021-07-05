"""Test AREDN node parsing functionality."""

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
    assert system_info.wlan_ip_address


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
    assert system_info.up_time_seconds == 9_578
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
    assert system_info.up_time_seconds == 22_042_803
    assert system_info.active_tunnel_count == 0
    assert not system_info.tunnel_installed
    assert len(system_info.services) == 1
    assert system_info.wlan_ip_address == "10.159.123.176"
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
    assert system_info.up_time_seconds == 330_245
    assert system_info.active_tunnel_count == 0
    assert not system_info.tunnel_installed
    assert system_info.wlan_ip_address == "10.106.204.11"
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
    assert system_info.wlan_ip_address == "10.154.255.82"
    assert system_info.lan_ip_address == "10.215.250.145"


def test_with_tunnel_1_7(data_folder):
    """Load information from a "tunnel" node"""

    with open(data_folder / "sysinfo-1.7-tunnel-installed.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

    # I could just construct a second object but I'm not checking everything
    assert system_info.node_name == "CALL1-HAPACL-300-P1"
    assert len(system_info.interfaces) == 8
    assert system_info.interfaces["eth0"].ip_address is None
    assert system_info.status == "on"
    assert system_info.ssid == "mesh-10-v3"
    assert system_info.api_version == "1.7"
    assert len(system_info.load_averages) == 3
    assert system_info.tunnel_installed
    assert isinstance(system_info.tunnel_installed, bool)
    assert system_info.active_tunnel_count == 0
    assert system_info.wlan_ip_address == "10.1.2.3"
    assert system_info.lan_ip_address == "10.3.2.1"


def test_with_tunnel_1_7_with_truish_tunnel_value(data_folder):
    """Load information from a "tunnel" node, check for type coercion"""

    with open(data_folder / "sysinfo-1.7-tunnel-installed.json", "r") as f:
        json_data = json.load(f)
        json_data["tunnels"]["tunnel_installed"] = "truish"
    system_info = aredn.load_system_info(json_data)

    # I could just construct a second object but I'm not checking everything
    assert system_info.node_name == "CALL1-HAPACL-300-P1"
    assert len(system_info.interfaces) == 8
    assert system_info.interfaces["eth0"].ip_address is None
    assert system_info.status == "on"
    assert system_info.ssid == "mesh-10-v3"
    assert system_info.api_version == "1.7"
    assert len(system_info.load_averages) == 3
    assert isinstance(system_info.tunnel_installed, bool)
    assert system_info.tunnel_installed is False
    assert system_info.active_tunnel_count == 0
    assert system_info.wlan_ip_address == "10.1.2.3"
    assert system_info.lan_ip_address == "10.3.2.1"


def test_with_tunnel_1_7_with_false_tunnel_value(data_folder):
    """Load information from a non-"tunnel" node Version 1.7"""

    with open(data_folder / "sysinfo-1.7-tunnel-installed.json", "r") as f:
        json_data = json.load(f)
        json_data["tunnels"]["tunnel_installed"] = False
    system_info = aredn.load_system_info(json_data)

    # I could just construct a second object but I'm not checking everything
    assert system_info.node_name == "CALL1-HAPACL-300-P1"
    assert len(system_info.interfaces) == 8
    assert system_info.interfaces["eth0"].ip_address is None
    assert system_info.status == "on"
    assert system_info.ssid == "mesh-10-v3"
    assert system_info.api_version == "1.7"
    assert len(system_info.load_averages) == 3
    assert isinstance(system_info.tunnel_installed, bool)
    assert system_info.tunnel_installed is False
    assert system_info.active_tunnel_count == 0
    assert system_info.wlan_ip_address == "10.1.2.3"
    assert system_info.lan_ip_address == "10.3.2.1"


def test_lan_interface_eth0_0(data_folder):
    """Validate that eth0.0 is recognized as a LAN IP address."""

    with open(data_folder / "sysinfo-1.5-no-location.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

    assert system_info.lan_ip_address == "10.66.236.21"


def test_wlan_mac_address_standardization(data_folder):
    """Confirm that MAC addresses are being standardized."""

    with open(data_folder / "sysinfo-1.7-link_info.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

    wlan_interface = system_info.wlan_interface
    assert wlan_interface.mac_address != system_info.wlan_mac_address
    assert ":" not in system_info.wlan_mac_address
    assert system_info.wlan_mac_address == system_info.wlan_mac_address.lower()


def test_radio_link_info_parsing(data_folder):
    """Confirm that radio link information is parsing correctly."""

    with open(data_folder / "sysinfo-1.7-link_info2.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

    assert len(system_info.links) == 3

    sample_link = system_info.links["10.150.4.228"]
    expected = aredn.Link(
        quality=0.94,
        neighbor_quality=0.94,
        signal=-82,
        noise=-91,
        type=aredn.LinkType.RADIO,
        hostname="N0CALL-RKM2-1-Medford-OR.local.mesh",
        tx_rate=19.5,
        rx_rate=26,
        olsr_interface="wlan0",
    )
    assert sample_link == expected


def test_dtd_link_info_parsing(data_folder):
    """Confirm that DTD link information is parsing correctly."""

    with open(data_folder / "sysinfo-1.7-link_info.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

    assert len(system_info.links) == 2

    sample_link = system_info.links["10.33.72.151"]
    expected = aredn.Link(
        quality=1,
        neighbor_quality=1,
        type=aredn.LinkType.DIRECT,
        hostname="N0CALL-VC-SHACK.local.mesh",
        olsr_interface="eth0.2",
    )
    assert sample_link == expected


def test_dtd_link_info_no_type(data_folder):
    """Confirm that DTD link information is parsing correctly."""

    with open(data_folder / "sysinfo-1.7-dtdlink-info.json", "r") as f:
        json_data = json.load(f)
    system_info = aredn.load_system_info(json_data)

    assert len(system_info.links) == 8

    sample_link = system_info.links["10.65.116.119"]
    expected = aredn.Link(
        quality=1,
        neighbor_quality=1,
        type=aredn.LinkType.DIRECT,
        hostname="N0CALL-NSM2-1-East-City-OR.local.mesh",
        olsr_interface="br-dtdlink",
    )
    assert sample_link == expected


def test_invalid_link_json():
    """Confirm that an unknown link is gracefully handled."""
    link_json = {
        "neighborLinkQuality": 1,
        "linkQuality": 1,
        "hostname": "N0CALL-NSM2.local.mesh",
        "olsrInterface": "eth.0",
        "linkType": "foobar",
    }
    link_info = aredn.Link.from_json(link_json)
    expected = aredn.Link(
        quality=1,
        neighbor_quality=1,
        type=aredn.LinkType.UNKNOWN,
        hostname="N0CALL-NSM2.local.mesh",
        olsr_interface="eth.0",
    )
    assert link_info == expected


def test_version_checker():
    checker = aredn.VersionChecker((3, 20, 2, 0), (1, 7))
    assert checker.firmware("3.20.2.0") == 0
    assert checker.api("1.7") == 0


def test_version_checker_develop():
    checker = aredn.VersionChecker((3, 20, 2, 0), (1, 7))
    assert checker.firmware("develop-169-d18d14f3") == -1


@pytest.mark.parametrize(
    "sample, standard, expected",
    [
        ("1.7", "1.7", 0),
        ("1.6", "1.7", 1),
        ("1.5", "1.7", 2),
        ("1.5", "2.0", 3),
        ("1.0", "3.0", 3),
        ("3.20.1", "3.20.1", 0),
        ("3.20.0", "3.20.1", 1),
        ("3.20.0", "3.20.2", 1),
        ("3.20.0", "3.20.3", 1),
        ("3.19.4", "3.20.1", 2),
        ("3.18.4", "3.20.1", 3),
        ("2.15.4", "3.3.0", 3),
        ("3.20", "3.20.1", 1),
    ],
)
def test_version_delta(sample, standard, expected):
    standard_parts = tuple(int(value) for value in standard.split("."))
    sample_parts = tuple(int(value) for value in sample.split("."))
    calculated = aredn._version_delta(sample_parts, standard_parts)
    assert calculated == expected
