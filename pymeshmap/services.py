"""Register services with Pyramid."""

from pyramid.config import Configurator

from .aredn import VersionChecker
from .config import AppConfig
from .poller import Poller


def includeme(config: Configurator):
    settings = config.get_settings()

    # Register the `Poller` singleton
    poller_config: AppConfig.Poller = settings["poller"]
    poller = Poller.from_config(poller_config)
    config.register_service(poller, Poller)

    # Register the `VersionChecker` singleton
    aredn_config: AppConfig.Aredn = settings["aredn"]
    version_checker = VersionChecker.from_config(aredn_config)
    config.register_service(version_checker, VersionChecker)
