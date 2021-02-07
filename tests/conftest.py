from pathlib import Path

import pytest

from pymeshmap.config import AppConfig


@pytest.fixture(scope="module")
def data_folder() -> Path:
    """Fixture to simplify accessing test data files."""
    return Path(__file__).parent / "data"


@pytest.fixture()
def app_config():
    return AppConfig.from_environ({"MESHMAP_POLLER_NODE": "127.0.0.1"})
