"""Script to scrub identifiable information out of test files.

Replaces SSIDs, call signs, latitude and longitude, and MAC addresses with random/fake
data, assuming we know the right places to look.

"""

import ipaddress
import json
import random
import re
import string
import typing as t

import click
import loguru
from faker import Faker

logger = loguru.logger
fake = Faker()
callsign_regex = re.compile(r"\d?[a-zA-Z]{1,2}\d{1,4}[a-zA-Z]{1,4}")


@click.command()
@click.argument("filename", type=click.File("r"))
@click.argument("output", type=click.File("w"))
def main(filename, output):
    """Scrub JSON files before adding to repository for tests."""

    sys_info = json.load(filename)
    # I'm assuming we always start with a dictionary
    scrubbed_info = scrub_dict(sys_info)
    json.dump(scrubbed_info, output, indent=2)


def scrub_unknown(key: str, value: t.Any) -> t.Any:
    if isinstance(value, dict):
        return scrub_dict(value)
    elif isinstance(value, list):
        return scrub_list(key, value)
    else:
        return scrub_scalar(key, value)


def scrub_dict(values: t.Dict[str, t.Any]) -> t.Dict:
    scrubbed_dict = {key: scrub_unknown(key, value) for key, value in values.items()}
    return scrubbed_dict


def scrub_list(key: str, values: t.List) -> t.List:
    scrubbed_list = [scrub_unknown(key, value) for value in values]
    return scrubbed_list


def scrub_scalar(key: str, value: t.Any) -> t.Any:
    if not key:
        logger.warning("Cannot scalar value without a key: {!r}", value)
        return value

    new_value = None

    if key == "ip":
        # version 1.0 has "none" as an IP address, so may sure it is valid first
        try:
            ipaddress.ip_address(value)
        except ValueError:
            pass
        else:
            new_value = fake.ipv4_private(address_class="a")
    if key == "lat" and value != "":
        new_value = f"{fake.latitude():.6f}"
    if key == "lon" and value != "":
        new_value = f"{fake.longitude():.6f}"
    if key == "mac" and value != "00:00:00:00":
        new_value = fake.mac_address().upper()
    if key in ("node", "hostname", "name", "link"):
        new_value = callsign_regex.sub("N0CALL", value)
    if key == "grid_square" and value != "":
        new_value = random_gridsquare()
    if key == "ssid":
        new_value = "ArednMeshNetwork"

    if new_value is not None and new_value != value:
        print(f"Rewrote {value!r} to {new_value!r}")
        return new_value

    return value


def random_gridsquare():
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
    main()
