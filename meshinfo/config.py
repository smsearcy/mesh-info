"""Configuration for Mesh Info from the environment."""

from __future__ import annotations

import enum
import functools
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import environ
import pendulum
import platformdirs
from dotenv import load_dotenv
from loguru import logger
from pyramid.config import Configurator

from .aredn import VersionChecker
from .historical import HistoricalStats
from .network import reverse_dns_lookup
from .poller import Poller

FOLDER_NAME = "mesh-info"
_DEFAULT_TILE_URL = "//stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg"
_DEFAULT_TILE_ATTRIBUTION = (
    "Map tiles by <a href='http://stamen.com'>Stamen Design</a>, "
    "under <a href='http://creativecommons.org/licenses/by/3.0'>CC BY 3.0</a>. "
    "Data by <a href='http://openstreetmap.org'>OpenStreetMap</a>, "
    "under <a href='http://www.openstreetmap.org/copyright'>ODbL</a>."
)


class Environment(enum.Enum):
    DEV = "development"
    PROD = "production"


def default_workers():
    """Defaults to Gunicorn recommendations."""
    if cpu_count := os.cpu_count():
        return cpu_count * 2 + 1
    else:
        return 1


@environ.config(prefix="MESH_INFO")
class AppConfig:
    @environ.config
    class Aredn:
        current_firmware: str = environ.var(default="3.22.8.0")
        current_api: str = environ.var(default="1.11")

    @environ.config
    class Collector:
        node_inactive: int = environ.var(default=7, converter=int)
        link_inactive: int = environ.var(default=1, converter=int)
        period: int = environ.var(default=5, converter=int)
        max_retries: int = environ.var(default=5, converter=int)

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
        tile_url: str = environ.var(default=_DEFAULT_TILE_URL)
        tile_attribution: str = environ.var(default=_DEFAULT_TILE_ATTRIBUTION)

    @environ.config
    class Poller:
        max_connections: int = environ.var(default=50, converter=int)
        connect_timeout: int = environ.var(default=10, converter=int)
        read_timeout: int = environ.var(default=15, converter=int)

    @environ.config
    class Web:
        bind: str = environ.var(default="0.0.0.0:8000")
        workers: int = environ.var(default=default_workers(), converter=int)
        # debug_hosts

    env: Environment = environ.var(default="production", converter=Environment)
    local_node: str = environ.var(default="localnode.local.mesh")
    log_level: str = environ.var(default="SUCCESS")
    site_name: str = environ.var(default="Mesh Info")
    data_dir: Path = environ.var(default="")

    aredn: Aredn = environ.group(Aredn)
    collector: Collector = environ.group(Collector)
    db: DB = environ.group(DB)
    map: Map = environ.group(Map)
    poller: Poller = environ.group(Poller)
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
    settings: Optional[Dict[str, Any]] = None, *, app_config: Optional[AppConfig] = None
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

    # define Jinja filters
    filters = settings.setdefault("jinja2.filters", {})
    filters.setdefault("duration", "meshinfo.filters.duration")
    filters.setdefault("in_tz", "meshinfo.filters.in_tz")
    filters.setdefault("local_tz", "meshinfo.filters.local_tz")

    if app_config.env == Environment.DEV:
        settings["pyramid.reload_all"] = True
        settings["pyramid.debug_authorization"] = False
        settings["pyramid.debug_notfound"] = False
        settings["pyramid.debug_routematch"] = False
        settings["pyramid.default_locale_name"] = "en"
        settings["debugtoolbar.max_visible_requests"] = 25

    else:
        settings["pyramid.reload_templates"] = False
        settings["pyramid.debug_authorization"] = False
        settings["pyramid.debug_notfound"] = False
        settings["pyramid.debug_routematch"] = False
        settings["pyramid.default_locale_name"] = "en"

    # configure logging
    logger.remove()
    logger.add(sys.stderr, level=app_config.log_level)

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
                # TODO: identify client?
                logger.warning(
                    "Invalid timezone specified: {} ({!r})",
                    request.cookies["local_tz"],
                    exc,
                )
                client_tz = server_timezone
            return client_tz.name
        else:
            return server_timezone.name

    config.add_request_method(lambda r: client_timezone(r), "timezone", reify=True)

    # Register services with `pyramid-services`

    # Register the `Poller` singleton
    # create reverse DNS lookup partial
    lookup_node_name = functools.partial(
        reverse_dns_lookup,
        dns_server=app_config.local_node,
    )
    poller = Poller.create(
        lookup_name=lookup_node_name,
        max_connections=app_config.poller.max_connections,
        connect_timeout=app_config.poller.connect_timeout,
        read_timeout=app_config.poller.read_timeout,
    )
    config.register_service(poller, Poller)

    # Register the `VersionChecker` singleton
    version_checker = VersionChecker.from_config(app_config.aredn)
    config.register_service(version_checker, VersionChecker)

    # Register the `HistoricalStats` singleton
    logger.info("RRDtool data directory: {}", app_config.rrd_dir)
    config.register_service(
        HistoricalStats(data_path=app_config.rrd_dir), HistoricalStats
    )

    config.scan(".views")

    config.commit()
    return config
