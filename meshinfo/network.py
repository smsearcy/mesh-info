"""Network utility functions."""

from __future__ import annotations

import asyncio
import random
import struct
import sys

import attrs
import structlog
from structlog.contextvars import bound_contextvars

if sys.version_info >= (3, 11):
    import asyncio as async_timeout
else:
    import async_timeout

logger = structlog.get_logger()


@attrs.define
class DnsHeader:
    """Standard DNS header information."""

    id: bytes
    flags1: int
    flags2: int
    question_count: int
    answer_count: int
    name_server_count: int
    additional_record_count: int


class _DnsClientProtocol(asyncio.DatagramProtocol):
    """Asynchronous UDP client for doing a reverse-DNS lookup.

    Based on https://docs.python.org/3/library/asyncio-protocol.html#udp-echo-client

    """

    def __init__(self, ip_address: str, on_con_lost: asyncio.Future):
        header, question = _dns_lookup_message(ip_address)
        self.ip_address = ip_address
        self.header_size = len(header)
        self.message = header + question
        self.on_con_lost = on_con_lost
        self.transport: asyncio.DatagramTransport | None = None
        self.received = b""

    def connection_made(  # type: ignore[override]
        self, transport: asyncio.DatagramTransport
    ):
        self.transport = transport
        self.transport.sendto(self.message)

    def datagram_received(self, data, addr):
        self.received = self._parse_response(data)
        self.transport.close()

    def error_received(self, exc):
        logger.warning("Error received", error=exc)

    def connection_lost(self, exc):
        self.on_con_lost.set_result(self.received)

    def _parse_response(self, response) -> str:
        """Get the name from the DNS response."""

        response_header = DnsHeader(
            *struct.unpack(">2sBBHHHH", response[: self.header_size])
        )
        response_code = response_header.flags2 & 0b1111
        if response_code == 3:
            logger.warning("DNS name error")
            return ""
        if response_code > 0:
            logger.warning("DNS error", repsonse_code=response_code)
            return ""

        if len(self.message) == len(response):
            # this error should have been caught above
            logger.warning("DNS response too short")
            return ""

        record = struct.unpack(
            ">HHHIH", response[len(self.message) : len(self.message) + 12]
        )
        name_length = record[-1]

        # use the length of the name to know how many bytes to grab here
        name = bytearray(
            response[len(self.message) + 12 : len(self.message) + 12 + name_length]
        )
        parts = []
        while name:
            length = name.pop(0)
            if length == 0:
                break
            parts.append(name[:length])
            del name[:length]
        return ".".join(part.decode() for part in parts).lower()


async def reverse_dns_lookup(
    ip_address: str, dns_server: str, *, fqdn: bool = False
) -> str:
    """Do a reverse DNS lookup to get the node name for the IP address.

    Returns an empty string in case of an error.

    Need to implement our own because we need to query AREDN node for DNS,
    cannot assume that the system running MeshInfo has DNS setup for that.

    """
    with bound_contextvars(ip_address=ip_address):
        logger.debug("Reverse DNS lookup", dns_server=dns_server)
        loop = asyncio.get_running_loop()
        on_con_lost = loop.create_future()
        transport, _protocol = await loop.create_datagram_endpoint(
            lambda: _DnsClientProtocol(ip_address, on_con_lost),
            remote_addr=(dns_server, 53),
        )

        try:
            # There was weird issues with the poller hanging, so I addd a timeout here
            # in case that was the issue.  I think a simultaneous upgrade to aiohttp
            # might have fixed the issue, but I'm leaving this in for good measure.
            async with async_timeout.timeout(5):
                response = await on_con_lost
        except Exception as exc:
            logger.exception("Error querying DNS server", error=exc)
            return ""
        finally:
            transport.close()

    if fqdn:
        return response
    return response.split(".", maxsplit=1)[0]


def _dns_lookup_message(ip_address: str) -> tuple[bytes, bytes]:
    """Construct the DNS query message for a reverse name lookup."""
    header = struct.pack(
        ">2sBBHHHH",
        random.randbytes(2),
        0b01,
        0b00,
        1,
        0,
        0,
        0,
    )
    lookup = b""
    # build the lookup from the IP address in reverse order
    # each octet preceded by its length
    for octet in reversed(ip_address.encode().split(b".")):
        lookup += len(octet).to_bytes(1, "big")
        lookup += octet
    lookup += b"\x07in-addr\x04arpa"
    question = struct.pack(f">{len(lookup)}sBHH", lookup, 0, 12, 1)
    return header, question
