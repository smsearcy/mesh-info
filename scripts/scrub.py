#!/bin/env python
"""Scrub JSON system info for inclusion in test data."""

from __future__ import annotations

import argparse
import json
import random
import re
import string
import sys
from typing import Any

import attr
from faker import Faker  # type: ignore


@attr.s
class ScrubJsonSample:
    """Remove potentially sensitive information from sample JSON for nodes.

    This is a class to enable (or at least simplify) saving a map of replacements
    so values can stay consistent in a file.

    """

    mapped_values: dict = attr.ib(factory=dict, init=False)
    fake: Faker = attr.ib(factory=Faker, init=False)

    def scrub_dict(self, values: dict[str, Any]) -> dict:
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

    def scrub_list(self, key: str, values: list) -> list:
        scrubbed_list = [self.scrub_unknown(key, value) for value in values]
        return scrubbed_list

    def scrub_scalar(self, key: str, value: Any) -> Any:
        if not key:
            print(f"Cannot scalar value without a key: {value!r}", file=sys.stderr)
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


def main(argv: list = None):
    """Scrub JSON files before adding to repository for tests."""
    # Scrub Sample Files
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "filename",
        type=argparse.FileType("r"),
        help="source file to scrub",
    )
    parser.add_argument(
        "output",
        type=argparse.FileType("w"),
        help="output file to write to",
    )

    args = parser.parse_args(argv)

    sys_info = json.load(args.filename)
    # I'm assuming we always start with a dictionary
    scrubber = ScrubJsonSample()
    scrubbed_info = scrubber.scrub_dict(sys_info)
    json.dump(scrubbed_info, args.output, indent=2)


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


if __name__ == "__main__":
    sys.exit(main())
