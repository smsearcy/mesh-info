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
        connect_timeout: int = environ.var(default=20, converter=int)
        read_timeout: int = environ.var(default=20, converter=int)

    @environ.config
    class Aredn:
        current_firmware: str = environ.var(default="3.20.3.1")
        current_api: str = environ.var(default="1.7")

    @environ.config
    class Collector:
        node_inactive: int = environ.var(default=7, converter=int)
        link_inactive: int = environ.var(default=1, converter=int)

    env: Environment = environ.var(default=Environment.PROD, converter=Environment)
    log_level: str = environ.var(default="SUCCESS")
    db_url: str = environ.var(
        default="postgresql+psycopg2://postgres:pyMeshMap@db:5432/postgres"
    )
    poller: Poller = environ.group(Poller)
    aredn: Aredn = environ.group(Aredn)
    collector: Collector = environ.group(Collector)


# walks up the folder path looking for `.env` file
# and loads into environment variables
load_dotenv()
app_config = environ.to_config(AppConfig)
