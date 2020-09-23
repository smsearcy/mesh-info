"""Configuration for pyMeshMap from the environment."""

from __future__ import annotations

import enum
import os
from typing import Any, Callable, Dict

from dotenv import load_dotenv


class Environment(enum.Enum):
    DEV = "development"
    PROD = "production"


def get_settings(settings: Dict[str, Any] = None) -> Dict[str, Any]:
    """Load application configuration from the environment.

    If settings are not provided then use sane defaults so the application can run.

    """
    # walks up the folder path looking for `.env` file
    # and loads into environment variables
    load_dotenv()

    if settings is None:
        settings = {}

    maybe_set(
        settings,
        "pymeshmap.env",
        "PYMESHMAP_ENV",
        default=Environment.PROD,
        converter=Environment,
    )
    maybe_set(
        settings,
        "pymeshmap.local_node",
        "PYMESHMAP_LOCAL_NODE",
        default="localnode.local.mesh",
    )
    maybe_set(settings, "pymeshmap.log_level", "PYMESHMAP_LOG_LEVEL", default="SUCCESS")

    # Configure the poller
    maybe_set(
        settings,
        "poller.max_connections",
        "POLLER_MAX_CONNECTIONS",
        default=50,
        converter=int,
    )
    # Timeouts are in seconds
    maybe_set(
        settings,
        "poller.connect_timeout",
        "POLLER_CONNECT_TIMEOUT",
        default=20,
        converter=int,
    )
    maybe_set(
        settings,
        "poller.read_timeout",
        "POLLER_READ_TIMEOUT",
        default=20,
        converter=int,
    )
    maybe_set(
        settings,
        "poller.total_timeout",
        "POLLER_TOTAL_TIMEOUT",
        default=None,
        converter=int,
    )

    maybe_set(
        settings,
        "database.url",
        "DATABASE_URL",
        default="mysql+mysqldb://meshmap:meshmap@localhost/node_map",
    )

    maybe_set(
        settings, "aredn.current_firmware", "AREDN_CURRENT_FIRMWARE", default="3.20.3.0"
    )
    maybe_set(
        settings,
        "aredn.current_api_version",
        "AREDN_CURRENT_API_VERSION",
        default="1.7",
    )

    return settings


def maybe_set(
    settings: Dict[str, Any],
    key: str,
    env_var: str,
    *,
    default: Any,
    converter: Callable = None,
):
    """Set missing values with either the environment or a provided default.

    Based on `warehouse.config.maybe_set()` (licensed under Apache 2.0)

    """
    if key in settings:
        return
    if env_var in os.environ:
        value = os.environ[env_var]
        if converter is not None:
            value = converter(value)
        settings[key] = value
    else:
        settings[key] = default
