from __future__ import annotations

from collections import deque

import pytest
from faker import Faker

from meshinfo import report
from meshinfo.aredn import Interface, SystemInfo, VersionChecker
from meshinfo.poller import NetworkInfo

fake = Faker()

SAMPLE_NODES = [
    SystemInfo(
        node_name="node1",
        display_name="node1",
        api_version="1.7",
        grid_square="",
        latitude=float(fake.latitude()),
        longitude=float(fake.longitude()),
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
        services_json=[],
        status="on",
        source_json={},
        up_time="3 days, 19:44:05",
        load_averages=[0.3, 0.2, 0.1],
    ),
    SystemInfo(
        node_name="node2",
        display_name="node2",
        api_version="1.7",
        grid_square="",
        latitude=float(fake.latitude()),
        longitude=float(fake.longitude()),
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
        services_json=[],
        status="on",
        source_json={},
        up_time="3 days, 19:44:05",
        load_averages=[0.3, 0.2, 0.1],
    ),
    SystemInfo(
        node_name="node3",
        display_name="node3",
        api_version="1.5",
        grid_square="",
        latitude=float(fake.latitude()),
        longitude=float(fake.longitude()),
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
        services_json=[],
        source_json={},
        up_time="365 days, 19:44:05",
        load_averages=[2, 3, 4],
    ),
    SystemInfo(
        node_name="node4",
        display_name="node4",
        api_version="1.1",
        grid_square="",
        latitude=float(fake.latitude()),
        longitude=float(fake.longitude()),
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
        services_json=[],
        source_json={},
        up_time="365 days, 19:44:05",
        load_averages=[2, 3, 4],
    ),
]


def test_report_main(mocker, app_config):
    mock_poller = mocker.AsyncMock(return_value=NetworkInfo(deque(), deque(), deque()))
    mocker.patch("meshinfo.report.poll_network", side_effect=mock_poller)

    version_checker = VersionChecker.from_config(app_config.aredn)

    report.main("localnode", version_checker, timeout=15, workers=25)
    mock_poller.assert_awaited_once_with(start_node="localnode", timeout=15, workers=25)


@pytest.mark.parametrize("node", SAMPLE_NODES)
def test_print_node(node, app_config):
    checker = report.VersionChecker.from_config(app_config.aredn)
    report.pprint_node(node, checker)
