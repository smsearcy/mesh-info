"""Configuration for pyMeshMap from the environment."""

from __future__ import annotations

import enum
import functools
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import appdirs
import environ
import pendulum
from dotenv import load_dotenv
from loguru import logger
from pyramid.config import Configurator

from .aredn import VersionChecker
from .historical import HistoricalStats
from .poller import network_info


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
        data_dir: str = environ.var(default="")

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

    settings["environment"] = app_config.env
    settings["site_name"] = app_config.site_name
    settings["log_level"] = app_config.log_level
    settings["db.url"] = app_config.db_url
    settings["db.pool_pre_ping"] = True
    settings["local_node"] = app_config.poller.node
    settings["poller"] = app_config.poller
    settings["aredn"] = app_config.aredn
    settings["collector"] = app_config.collector
    settings["web"] = app_config.web

    # define Jinja filters
    filters = settings.setdefault("jinja2.filters", {})
    filters.setdefault("duration", "pymeshmap.filters.duration")
    filters.setdefault("in_tz", "pymeshmap.filters.in_tz")
    filters.setdefault("local_tz", "pymeshmap.filters.local_tz")

    if app_config.env == Environment.DEV:
        settings["pyramid.reload_all"] = True
        settings["pyramid.debug_authorization"] = False
        settings["pyramid.debug_notfound"] = False
        settings["pyramid.debug_routematch"] = False
        settings["pyramid.default_locale_name"] = "en"
    else:
        settings["pyramid.reload_templates"] = False
        settings["pyramid.debug_authorization"] = False
        settings["pyramid.debug_notfound"] = False
        settings["pyramid.debug_routematch"] = False
        settings["pyramid.default_locale_name"] = "en"

    # configure logging
    logger.remove()
    logger.add(sys.stderr, level=settings["log_level"])

    # configure Pyramid application
    config = Configurator(settings=settings)

    config.add_settings({"pyramid.retry": 3})

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

    # Register the `Poller` singleton
    poller = functools.partial(
        network_info,
        max_connections=app_config.poller.max_connections,
        connect_timeout=app_config.poller.connect_timeout,
        read_timeout=app_config.poller.read_timeout,
    )
    config.register_service(poller, name="poller")

    # Register the `VersionChecker` singleton
    version_checker = VersionChecker.from_config(app_config.aredn)
    config.register_service(version_checker, VersionChecker)

    # Register the `HistoricalStats` singleton
    collector_config: AppConfig.Collector = settings["collector"]
    if collector_config.data_dir:
        data_dir = Path(collector_config.data_dir)
    elif settings["environment"] == Environment.DEV:
        # should the name really be hard-coded?
        data_dir = Path(appdirs.user_data_dir("pymeshmap"))
    else:
        data_dir = Path(appdirs.site_data_dir("pymeshmap"))
    logger.info("Collector data path: {}", data_dir)
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    config.register_service(HistoricalStats(data_path=data_dir), HistoricalStats)

    config.scan(".views")

    config.commit()
    return config
