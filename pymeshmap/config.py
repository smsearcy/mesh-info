"""Configuration for pyMeshMap from the environment."""

import enum
import os
from typing import Any, Callable, Dict


class Environment(enum.Enum):
    DEV = "development"
    PROD = "production"


# use python-dotenv to load a `.env` file


def get_settings(settings: Dict[str, Any] = None) -> Dict[str, Any]:
    """Load application configuration from the environment.

    If settings are not provided then use sane defaults so the application can run.

    """
    if settings is None:
        settings = {}

    _set_missing(
        settings, "pymeshmap.env", "PYMESHMAP_ENV", Environment.PROD, Environment
    )
    _set_missing(
        settings, "pymeshmap.local_node", "PYMESHMAP_LOCAL_NODE", "localnode.local.mesh"
    )
    _set_missing(settings, "pymeshmap.log_level", "PYMESHMAP_LOG_LEVEL", "SUCCESS")
    _set_missing(settings, "pymeshmap.max_polling", "PYMESHMAP_MAX_POLLING", 100, int)

    _set_missing(
        settings,
        "database.url",
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:pyMeshMap@localhost:5432/postgres",
    )

    # Should these be settings in the database?
    _set_missing(
        settings, "aredn.current_firmware", "AREDN_CURRENT_FIRMWARE", "3.20.3.0"
    )
    _set_missing(
        settings, "aredn.current_api_version", "AREDN_CURRENT_API_VERSION", "1.7"
    )

    return settings


def _set_missing(
    settings: Dict[str, Any],
    key: str,
    env_var: str,
    default: Any,
    converter: Callable = None,
):
    """Set missing values with either the environment or a provided default."""
    if key in settings:
        return
    elif env_var in os.environ and converter is not None:
        settings[key] = converter(os.environ[env_var])
    elif env_var in os.environ:
        settings[key] = os.environ[env_var]
    else:
        settings[key] = default
