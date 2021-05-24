"""Main entry point for the Pyramid web application."""

from typing import Any, Dict

import hupper
import pendulum
import waitress
from loguru import logger
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
    # Used for Pyramid testing
    settings.update(**kwargs)

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

    with Configurator(settings=settings) as config:
        config.include("pyramid_services")
        config.include("pyramid_jinja2")
        config.include(".routes")
        config.include(".models")

        if app_config.env == Environment.DEV:
            config.include("pyramid_debugtoolbar")

        server_timezone = pendulum.local_timezone()

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

        config.scan(".views")

    return config.make_wsgi_app()


def app_factory(global_config, **settings):
    from .config import app_config

    return make_wsgi_app(app_config, **settings)
