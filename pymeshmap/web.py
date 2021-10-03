"""Main entry point for the Pyramid web application."""

from __future__ import annotations

import hupper
import waitress
from loguru import logger
from pyramid.config import Configurator

from .config import configure


def main(
    config: Configurator, *, host: str = "", port: int = None, reload: bool = False
):
    """Create and run the Pyramid WSGI application."""

    if reload:
        reloader = hupper.start_reloader("pymeshmap.cli.main")
        reloader.watch_files([".env"])

    settings = config.get_settings()
    host = host or settings["web"].host
    port = port or settings["web"].port
    logger.info("Web server listening on {}:{}", host, port)

    waitress.serve(config.make_wsgi_app(), host=host, port=port)


def app_factory(global_config, **settings):
    config = configure(settings)

    return config.make_wsgi_app()
