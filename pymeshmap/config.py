"""Configuration for pyMeshMap from the environment."""

from __future__ import annotations

import enum

import environ
from dotenv import load_dotenv

__all__ = ["Environment", "AppConfig", "app_config"]


class Environment(enum.Enum):
    DEV = "development"
    PROD = "production"


@environ.config(prefix="MESHMAP")
class AppConfig:
    @environ.config
    class Poller:
        node: str = environ.var(default="localnode.local.mesh")
        max_connections: int = environ.var(default=50, converter=int)
        connect_timeout: int = environ.var(default=10, converter=int)
        read_timeout: int = environ.var(default=15, converter=int)

    @environ.config
    class Aredn:
        current_firmware: str = environ.var(default="3.20.3.1")
        current_api: str = environ.var(default="1.7")

    @environ.config
    class Collector:
        node_inactive: int = environ.var(default=7, converter=int)
        link_inactive: int = environ.var(default=1, converter=int)
        period: int = environ.var(default=5, converter=int)
        max_retries: int = environ.var(default=5, converter=int)

    @environ.config
    class Web:
        host: str = environ.var(default="127.0.0.1")
        port: int = environ.var(default=6543, converter=int)
        # debug_hosts

    env: Environment = environ.var(default="production", converter=Environment)
    log_level: str = environ.var(default="SUCCESS")
    db_url: str = environ.var(
        default="postgresql+psycopg2://postgres:@localhost:5432/postgres"
    )
    site_name: str = environ.var(default="pyMeshMap")

    poller: Poller = environ.group(Poller)
    aredn: Aredn = environ.group(Aredn)
    collector: Collector = environ.group(Collector)
    web: Web = environ.group(Web)


# walks up the folder path looking for `.env` file
# and loads into environment variables
load_dotenv()
app_config = environ.to_config(AppConfig)
