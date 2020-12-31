"""Functionality for scrubbing JSON system info."""

from __future__ import annotations

import json
import random
import re
import string
from typing import Any, Dict, List

import attr
import click
from faker import Faker  # type: ignore
from loguru import logger


@attr.s
class ScrubJsonSample:
    """Remove potentially sensitive information from sample JSON for nodes.

    This is a class to enable (or at least simplify) saving a map of replacements
    so values can stay consistent in a file.

    """

    mapped_values: Dict = attr.ib(factory=dict, init=False)
    fake: Faker = attr.ib(factory=Faker, init=False)

    def scrub_dict(self, values: Dict[str, Any]) -> Dict:
        scrubbed_dict = {
            key: self.scrub_unknown(key, value) for key, value in values.items()
        }
        return scrubbed_dict

    def scrub_unknown(self, key: str, value: Any) -> Any:
        if isinstance(value, dict):
            return self.scrub_dict(value)
        elif isinstance(value, list):
            return self.scrub_list(key, value)
        else:
            return self.scrub_scalar(key, value)

    def scrub_list(self, key: str, values: List) -> List:
        scrubbed_list = [self.scrub_unknown(key, value) for value in values]
        return scrubbed_list

    def scrub_scalar(self, key: str, value: Any) -> Any:
        if not key:
            logger.warning("Cannot scalar value without a key: {!r}", value)
            return value

        new_value = None

        if key == "lat" and value != "":
            new_value = f"{self.fake.latitude():.6f}"
        elif key == "lon" and value != "":
            new_value = f"{self.fake.longitude():.6f}"
        elif key == "mac" and value != "00:00:00:00":
            # due to virtual interfaces the same MAC address can repeat in the file
            if value not in self.mapped_values:
                self.mapped_values[value] = self.fake.mac_address().upper()
            new_value = self.mapped_values[value]
        elif key in ("node", "hostname", "name", "link"):
            new_value = re.sub(r"\d?[a-zA-Z]{1,2}\d{1,4}[a-zA-Z]{1,4}", "N0CALL", value)
        elif key == "grid_square" and value != "":
            new_value = random_grid_square()
        elif key == "ssid":
            new_value = "ArednMeshNetwork"

        if new_value is not None and new_value != value:
            print(f"Rewrote {value!r} to {new_value!r}")
            return new_value

        return value


@click.command(help="Scrub identifiable information from data files for testing.")
@click.argument("filename", type=click.File("r"))
@click.argument("output", type=click.File("w"))
def main(filename, output):
    """Scrub JSON files before adding to repository for tests."""

    sys_info = json.load(filename)
    # I'm assuming we always start with a dictionary
    scrubber = ScrubJsonSample()
    scrubbed_info = scrubber.scrub_dict(sys_info)
    json.dump(scrubbed_info, output, indent=2)


def random_grid_square():
    """Generate a random MaidenHead grid square value."""
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    values = [
        random.randint(0, 17),
        random.randint(0, 17),
        random.randint(0, 9),
        random.randint(0, 9),
        random.randint(0, 24),
        random.randint(0, 24),
    ]
    grid_square = (
        uppercase[values[0]]
        + uppercase[values[1]]
        + f"{values[2]}{values[3]}"
        + lowercase[values[4]]
        + lowercase[values[5]]
    )
    return grid_square
