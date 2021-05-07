"""Main entry point for the Pyramid web application."""

from typing import Any, Dict

import hupper
import waitress
from pyramid.config import Configurator

from .config import AppConfig, Environment


def main(
    app_config: AppConfig, *, host: str = "", port: int = None, reload: bool = False
):
    """Create and run the Pyramid WSGI application."""

    if reload:
        reloader = hupper.start_reloader("pymeshmap.cli.main")
        reloader.watch_files([".env"])

    app = make_wsgi_app(app_config)

    host = host or app_config.web.host
    port = port or app_config.web.port

    waitress.serve(app, host=host, port=port)


def make_wsgi_app(app_config: AppConfig, **kwargs):
    """Create the Pyramid WSGI application"""

    settings: Dict[str, Any] = {
        "app_config": app_config,
    }
    # Use for Pyramid testing
    settings.update(**kwargs)

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

    with Configurator(settings=settings) as config:
        config.include("pyramid_mako")
        config.include("pyramid_services")
        config.include(".routes")
        config.include(".models")

        if app_config.env == Environment.DEV:
            config.include("pyramid_debugtoolbar")

        config.scan(".views")

    return config.make_wsgi_app()


def app_factory(global_config, **settings):
    from .config import app_config

    return make_wsgi_app(app_config, **settings)
