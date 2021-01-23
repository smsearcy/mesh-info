"""Test network crawling functionality."""

import sys
from asyncio import StreamReader, StreamWriter

import pytest

from pymeshmap import poller


def olsr_records(filename):
    """Simulate OLSR data from a file."""
    with open(filename, "rb") as f:
        for line in f:
            yield line

        yield b""


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")
@pytest.mark.asyncio
async def test_olsr_nodes(data_folder, mocker):
    reader = mocker.Mock(spec=StreamReader)
    reader.readline = mocker.AsyncMock(
        side_effect=olsr_records(data_folder / "olsr-dump.txt")
    )
    writer = mocker.Mock(spec=StreamWriter)
    olsr_data = poller.OlsrData(reader, writer)
    nodes = [node async for node in olsr_data.nodes]

    assert len(nodes) == 23
    assert nodes[0] == "10.122.183.8"
    assert len(set(nodes)) == len(nodes)


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")
@pytest.mark.asyncio
async def test_olsr_links(data_folder, mocker):
    reader = mocker.Mock(spec=StreamReader)
    reader.readline = mocker.AsyncMock(
        side_effect=olsr_records(data_folder / "olsr-dump.txt")
    )
    writer = mocker.Mock(spec=StreamWriter)
    olsr_data = poller.OlsrData(reader, writer)
    links = [link async for link in olsr_data.links]

    assert len(links) == 96
    assert links[0] == poller.LinkInfo("10.22.15.88", "10.98.33.29", 2.986)


@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")
@pytest.mark.asyncio
async def test_olsr_async_data(data_folder, mocker):
    reader = mocker.Mock(spec=StreamReader)
    reader.readline = mocker.AsyncMock(
        side_effect=olsr_records(data_folder / "olsr-dump.txt")
    )
    writer = mocker.Mock(spec=StreamWriter)
    olsr_data = poller.OlsrData(reader, writer)

    nodes = []
    for _ in range(10):
        nodes.append(await olsr_data.nodes.__anext__())

    links = [link async for link in olsr_data.links]
    assert len(links) == 96

    for _ in range(13):
        nodes.append(await olsr_data.nodes.__anext__())

    assert len(nodes) == 23

    with pytest.raises(StopAsyncIteration):
        await olsr_data.nodes.__anext__()
