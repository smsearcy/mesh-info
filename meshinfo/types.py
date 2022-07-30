"""Define some widely used types."""
# This module shouldn't import anything to avoid circular imports!

from __future__ import annotations

import enum
from typing import Optional

import attr


@attr.s(auto_attribs=True, slots=True)
class LinkId:
    """Uniquely identifies a link by database keys."""

    source: int
    destination: int
    type: LinkType

    @classmethod
    def from_url(cls, params: dict) -> Optional[LinkId]:
        """Create `LinkId` object from path parameters."""

        try:
            source = int(params["source"])
            destination = int(params["destination"])
            type_ = getattr(params["type"], params["type"].upper())
        except Exception:
            return None

        return LinkId(source, destination, type_)

    def dump(self) -> str:
        """Serialize link to string.

        Useful for naming files, etc.

        """
        return f"{self.source}-{self.destination}-{self.type.name.lower()}"


class LinkStatus(enum.Enum):
    """Enumerate possible statuses for links."""

    CURRENT = enum.auto()
    RECENT = enum.auto()
    INACTIVE = enum.auto()

    def __str__(self):
        return self.name.title()


class LinkType(enum.IntEnum):
    """Enumerate types of links.

    Implemented as `IntEnum` so that we can sort by it.

    """

    DTD = 1
    TUN = 2
    RF = 3
    UNKNOWN = 99

    def __str__(self):
        # using if...else since it's not a straight-forward `.title()`
        if self == LinkType.RF:
            return "Radio"
        elif self == LinkType.TUN:
            return "Tunnel"
        elif self == LinkType.DTD:
            return "DTD"
        else:
            return "Unknown"


class NodeStatus(enum.Enum):
    """Enumerate possible polling statuses for nodes."""

    ACTIVE = enum.auto()
    INACTIVE = enum.auto()

    def __str__(self):
        return self.name.title()


class Band(enum.Enum):
    """Enumerate possible AREDN mesh bands."""

    # These values need to stay consistent because they are used in the database
    NINE_HUNDRED_MHZ = "900MHz"
    TWO_GHZ = "2GHz"
    THREE_GHZ = "3GHz"
    FIVE_GHZ = "5GHz"
    UNKNOWN = "Unknown"
    OFF = ""

    def __str__(self):
        labels = {
            Band.NINE_HUNDRED_MHZ: "900 MHz",
            Band.TWO_GHZ: "2 GHz",
            Band.THREE_GHZ: "3 GHz",
            Band.FIVE_GHZ: "5 GHz",
            Band.UNKNOWN: "Unknown",
            Band.OFF: "RF Off",
        }
        return labels.get(self, "Unknown")
