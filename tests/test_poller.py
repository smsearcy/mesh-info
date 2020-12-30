"""Test network crawling functionality."""

import pytest

from pymeshmap import poller


async def olsr_records(filename):
    """Simulate `_query_olsr()` with data from a file."""
    with open(filename, "r") as f:
        for line in f:
            yield line.rstrip()


@pytest.mark.asyncio
async def test_get_nodes(data_folder):
    """Test the parsing of nodes from the OLSR data."""
    records = olsr_records(data_folder / "olsr-dump.txt")
    nodes = [node async for node in poller._get_node_addresses(records)]

    assert len(nodes) == 23
    assert nodes[0] == "10.122.183.8"


@pytest.mark.asyncio
async def test_get_nodes_unique(data_folder):
    """Verify that the node parser is only returning unique nodes."""
    records = olsr_records(data_folder / "olsr-dump.txt")
    nodes = [node async for node in poller._get_node_addresses(records)]

    assert len(set(nodes)) == len(nodes)


@pytest.mark.asyncio
async def test_get_link_info(data_folder):
    records = olsr_records(data_folder / "olsr-dump.txt")
    links = [link async for link in poller._get_node_links(records)]

    assert len(links) == 96
    assert links[0] == poller.LinkInfo("10.22.15.88", "10.98.33.29", 2.986)
