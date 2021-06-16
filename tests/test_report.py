import sys

import pytest
from faker import Faker

from pymeshmap import report
from pymeshmap.aredn import Interface, SystemInfo, VersionChecker
from pymeshmap.poller import NetworkInfo, network_info

fake = Faker()

SAMPLE_NODES = [
    SystemInfo(
        node_name="node1",
        api_version="1.7",
        grid_square="",
        latitude=fake.latitude(),
        longitude=fake.longitude(),
        interfaces={
            "wlan0": Interface("wlan0", fake.mac_address(), fake.ipv4_private()),
            "eth0": Interface("eth0", fake.mac_address(), fake.ipv4_private()),
        },
        ssid="ArednMeshNetwork",
        channel="177",
        channel_bandwidth="20",
        frequency="5.885 GHz",
        model="Unknown",
        board_id="Unknown",
        firmware_manufacturer="AREDN",
        firmware_version="3.20.3.0",
        active_tunnel_count=0,
        tunnel_installed=False,
        services=[],
        services_json=[],
        status="on",
        source_json={},
        up_time="3 days, 19:44:05",
        load_averages=[0.3, 0.2, 0.1],
    ),
    SystemInfo(
        node_name="node2",
        api_version="1.7",
        grid_square="",
        latitude=fake.latitude(),
        longitude=fake.longitude(),
        interfaces={
            "wlan0": Interface("wlan0", fake.mac_address(), fake.ipv4_private()),
            "eth0": Interface("eth0", fake.mac_address(), fake.ipv4_private()),
        },
        ssid="ArednMeshNetwork",
        channel="-2",
        channel_bandwidth="10",
        frequency="2.397 GHz",
        model="Unknown",
        board_id="Unknown",
        firmware_manufacturer="AREDN",
        firmware_version="3.20.3.0",
        active_tunnel_count=0,
        tunnel_installed=False,
        services=[],
        services_json=[],
        status="on",
        source_json={},
        up_time="3 days, 19:44:05",
        load_averages=[0.3, 0.2, 0.1],
    ),
    SystemInfo(
        node_name="node3",
        api_version="1.5",
        grid_square="",
        latitude=fake.latitude(),
        longitude=fake.longitude(),
        interfaces={
            "wlan0": Interface("wlan0", fake.mac_address(), fake.ipv4_private()),
            "eth0": Interface("eth0", fake.mac_address(), fake.ipv4_private()),
        },
        status="off",
        ssid="",
        channel="",
        channel_bandwidth="",
        frequency="",
        model="Unknown",
        board_id="Unknown",
        firmware_manufacturer="AREDN",
        firmware_version="3.18.0.0",
        active_tunnel_count=0,
        tunnel_installed=False,
        services=[],
        services_json=[],
        source_json={},
        up_time="365 days, 19:44:05",
        load_averages=[2, 3, 4],
    ),
    SystemInfo(
        node_name="node4",
        api_version="1.1",
        grid_square="",
        latitude=fake.latitude(),
        longitude=fake.longitude(),
        interfaces={
            "wlan0": Interface("wlan0", fake.mac_address(), fake.ipv4_private()),
            "eth0": Interface("eth0", fake.mac_address(), fake.ipv4_private()),
        },
        status="off",
        ssid="",
        channel="",
        channel_bandwidth="",
        frequency="",
        model="Unknown",
        board_id="Unknown",
        firmware_manufacturer="AREDN",
        firmware_version="develop-169-d18d14f3",
        active_tunnel_count=0,
        tunnel_installed=False,
        services=[],
        services_json=[],
        source_json={},
        up_time="365 days, 19:44:05",
        load_averages=[2, 3, 4],
    ),
]


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")
def test_report_main(mocker, app_config):
    mock_poller = mocker.AsyncMock(return_value=NetworkInfo([], [], {}))
    mocker.patch("pymeshmap.report.network_info", side_effect=mock_poller)

    version_checker = VersionChecker.from_config(app_config.aredn)

    report.main("localnode", network_info, version_checker)
    mock_poller.assert_awaited_once_with("localnode", network_info)


@pytest.mark.parametrize("node", SAMPLE_NODES)
def test_print_node(node, app_config):
    checker = report.VersionChecker.from_config(app_config.aredn)
    report.pprint_node(node, checker)
