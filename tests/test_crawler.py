"""Test network crawling functionality."""

import pytest

from pymeshmap import crawler


async def olsr_records(filename):
    """Simulate `_query_olsr()` with data from a file."""
    with open(filename, "r") as f:
        for line in f:
            yield line.rstrip()


@pytest.mark.asyncio
async def test_get_nodes(data_folder):
    """Verify some basic information about `crawler.get_nodes()`"""
    records = olsr_records(data_folder / "olsr-dump.txt")
    nodes = [node async for node in crawler.get_nodes(records)]

    assert len(nodes) == 23
    assert nodes[0] == "10.122.183.8"


@pytest.mark.asyncio
async def test_get_nodes_unique(data_folder):
    """Verify that the node parser is only returning unique nodes."""
    records = olsr_records(data_folder / "olsr-dump.txt")
    nodes = [node async for node in crawler.get_nodes(records)]

    assert len(set(nodes)) == len(nodes)


@pytest.mark.asyncio
async def test_get_nodes_ignore_hosts(data_folder):
    """Verify that ignored hosts are excluded from the node list."""
    records = olsr_records(data_folder / "olsr-dump.txt")
    nodes = {
        node async for node in crawler.get_nodes(records, ignore_hosts={"10.122.183.8"})
    }

    assert "10.122.183.8" not in nodes
    assert len(nodes) == 22


@pytest.mark.asyncio
async def test_get_link_info(data_folder):
    records = olsr_records(data_folder / "olsr-dump.txt")
    links = [link async for link in crawler.get_links(records)]

    assert len(links) == 96
