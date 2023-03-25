"""Test network crawling functionality."""

from asyncio import StreamReader

import pytest

from meshinfo import poller


def olsr_records(filename):
    """Simulate OLSR data from a file."""
    with open(filename, "rb") as f:
        for line in f:
            yield line

        yield b""


@pytest.mark.asyncio
async def test_olsr_nodes(data_folder, mocker):
    reader = mocker.Mock(spec=StreamReader)
    reader.readline = mocker.AsyncMock(
        side_effect=olsr_records(data_folder / "olsr-dump.txt")
    )
    olsr_data = await poller._process_olsr_data(reader)
    nodes = sorted(olsr_data.nodes)

    assert len(nodes) == 23
    assert nodes[0] == "10.104.91.20"


@pytest.mark.asyncio
async def test_olsr_links(data_folder, mocker):
    reader = mocker.Mock(spec=StreamReader)
    reader.readline = mocker.AsyncMock(
        side_effect=olsr_records(data_folder / "olsr-dump.txt")
    )
    olsr_data = await poller._process_olsr_data(reader)
    assert len(olsr_data.links_by_source) == 23
    expected = poller.TopoLink("10.22.15.88", "10.98.33.29", 2.986)
    assert expected in olsr_data.links_by_source["10.22.15.88"]
    links = list(olsr_data.links)
    assert len(links) == 96
