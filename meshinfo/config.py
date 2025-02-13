"""Configuration for Mesh Info from the environment."""

from __future__ import annotations

import enum
import logging
import os
from pathlib import Path
from typing import Any

import attrs
import environ
import pendulum
import platformdirs
import structlog
from dotenv import load_dotenv
from pyramid.config import Configurator

from .aredn import VersionChecker
from .historical import HistoricalStats

logger = structlog.get_logger()

FOLDER_NAME = "mesh-info"


class Environment(enum.Enum):
    DEV = "development"
    PROD = "production"


def default_workers():
    """Defaults to Gunicorn recommendations."""
    if cpu_count := os.cpu_count():
        return cpu_count * 2 + 1
    else:
        return 1


def _get_log_level(level: str) -> int:
    return getattr(logging, level)


@environ.config(prefix="MESH_INFO")
class AppConfig:
    @environ.config
    class Aredn:
        current_firmware: str = environ.var(default="3.25.2.0")
        current_api: str = environ.var(default="1.13")

    @environ.config
    class Collector:
        workers: int = environ.var(default=50, converter=int)
        timeout: int = environ.var(default=30, converter=int)
        node_inactive: int = environ.var(default=7, converter=int)
        link_inactive: int = environ.var(default=1, converter=int)
        period: int = environ.var(default=5, converter=int)

    @environ.config
    class DB:
        url: str = environ.var(default="")
        pool_pre_ping: bool = environ.bool_var(default=True)

    @environ.config
    class Map:
        latitude: float = environ.var(default=19.64, converter=float)
        longitude: float = environ.var(default=-1.58, converter=float)
        zoom: int = environ.var(default=3, converter=int)
        max_zoom: int = environ.var(default=18, converter=int)
        tile_url: str = environ.var(default="")
        tile_attribution: str = environ.var(default="")

    @environ.config
    class Web:
        bind: str = environ.var(default="0.0.0.0:8000")
        workers: int = environ.var(default=default_workers(), converter=int)
        # debug_hosts

    env: Environment = environ.var(default="production", converter=Environment)
    local_node: str = environ.var(default="localnode.local.mesh")
    log_level: int = environ.var(default="WARNING", converter=_get_log_level)
    site_name: str = environ.var(default="Mesh Info")
    data_dir: Path = environ.var(default="")

    aredn: Aredn = environ.group(Aredn)
    collector: Collector = environ.group(Collector)
    db: DB = environ.group(DB)
    map: Map = environ.group(Map)
    web: Web = environ.group(Web)

    def __attrs_post_init__(self):
        if self.data_dir == "":
            # default data directory depends on environment
            if self.env == Environment.PROD:
                self.data_dir = Path(f"/var/lib/{FOLDER_NAME}")
            elif self.env == Environment.DEV:
                self.data_dir = platformdirs.user_data_path(FOLDER_NAME) / "data"
        else:
            self.data_dir = Path(self.data_dir)

        if self.db.url == "":
            # location of default SQLite database depends on the data_dir
            self.db.url = f"sqlite:///{self.data_dir!s}/mesh-info.db"

        if self.env == Environment.DEV:
            # Only use 1 worker in development environment for the debug toolbar
            self.web.workers = 1

    @property
    def rrd_dir(self) -> Path:
        """Directory for RRD files under the data directory."""
        return self.data_dir / "rrd"


def from_env() -> AppConfig:
    # walks up the folder path looking for `.env` file
    # and loads into environment variables
    # (which we then put into the settings dictionary)
    load_dotenv()
    return environ.to_config(AppConfig)


def configure(
    settings: dict[str, Any] | None = None, *, app_config: AppConfig | None = None
) -> Configurator:
    """Configure the Pyramid application."""

    if settings is None:
        settings = {}

    if app_config is None:
        app_config = from_env()

    # This is kind of ugly since I'm mashing together
    # (I should update my custom stuff to just use the AppConfig object)
    settings["app_config"] = app_config

    # Configure settings for Pyramid
    settings["pyramid.retry"] = 3

    # Configure Jinja2
    settings["jinja2.directories"] = "meshinfo:templates"
    settings["jinja2.filters"] = {
        "duration": "meshinfo.filters.duration",
        "in_tz": "meshinfo.filters.in_tz",
        "local_tz": "meshinfo.filters.local_tz",
        "unknown": "meshinfo.filters.unknown",
    }

    if app_config.env == Environment.DEV:
        settings["debugtoolbar.max_visible_requests"] = 25
        settings["pyramid.debug_authorization"] = False
        settings["pyramid.debug_notfound"] = False
        settings["pyramid.debug_routematch"] = False
        settings["pyramid.prevent_cachebust"] = True
        settings["pyramid.reload_all"] = True

    # configure logging
    configure_logging(app_config.log_level)

    logger.debug(
        "Application configuration",
        **attrs.asdict(app_config),  # type: ignore
    )

    # configure Pyramid application
    config = Configurator(settings=settings)

    config.include("pyramid_retry")
    config.include("pyramid_services")
    config.include("pyramid_jinja2")
    config.include(".routes")
    config.include(".models")

    if app_config.env == Environment.DEV:
        config.include("pyramid_debugtoolbar")

    server_timezone = pendulum.tz.local_timezone()

    def client_timezone(request):
        if "local_tz" in request.cookies:
            try:
                client_tz = pendulum.timezone(request.cookies["local_tz"])
            except Exception as exc:
                logger.warning(
                    "Invalid timezone specified",
                    local_tz=request.cookies["local_tz"],
                    error=repr(exc),
                )
                client_tz = server_timezone
            return client_tz.name
        else:
            return server_timezone.name

    config.add_request_method(lambda r: client_timezone(r), "timezone", reify=True)

    # Register services with `pyramid-services`

    # Register the `VersionChecker` singleton
    version_checker = VersionChecker.from_config(app_config.aredn)
    config.register_service(version_checker, VersionChecker)

    # Register the `HistoricalStats` singleton
    config.register_service(
        HistoricalStats(data_path=app_config.rrd_dir), HistoricalStats
    )

    config.scan(".views")

    config.commit()
    return config


def configure_logging(level: int):
    """Configure structlog with the specified level."""
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    if "INVOCATION_ID" not in os.environ:
        # add timestamps when not running in systemd
        processors.append(structlog.processors.TimeStamper(fmt="iso", utc=False))
    # TODO: do we need a way to disable colors?  (doesn't work with redirecting output)
    processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
