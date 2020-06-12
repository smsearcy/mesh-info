"""Script to scrub identifiable information out of test files.

Replaces SSIDs, call signs, latitude and longitude, and MAC addresses with random/fake
data, assuming we know the right places to look.

"""

import re

import click
from faker import Faker

callsign_regex = re.compile(r"\d?[a-zA-Z]{1,2}\d{1,4}[a-zA-Z]{1,4}")
