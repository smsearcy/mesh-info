import hashlib
import subprocess
from pathlib import Path

from pyramid.config import Configurator
from pyramid.static import QueryStringCacheBuster

from meshinfo import __version__


class CacheBuster(QueryStringCacheBuster):
    """Add query string parameter to static assets for busting cache on updates.

    Uses Git commit SHA1 if available, otherwise the app version.

    """

    def __init__(self, param="x", repo_path=None):
        super().__init__(param=param)
        if repo_path is None:
            repo_path = Path(__file__).parent.absolute()
        try:
            self.sha1 = subprocess.run(
                ("git", "rev-parse", "HEAD"),
                cwd=repo_path,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout.decode()[:12]
        except OSError:
            # hash the current version of the application
            hash_ = hashlib.md5()
            hash_.update(__version__.encode())
            self.sha1 = hash_.hexdigest()[:12]

    def tokenize(self, request, pathspec, kw):
        return self.sha1


def includeme(config: Configurator):
    """Configure application routes."""

    config.add_static_view("static", "static")
    config.add_cache_buster("static", CacheBuster())

    config.add_route("home", "/")
    config.add_route("iperf-tool", "/iperf-tool")
    config.add_route("about", "/about")
    config.add_route("map", "/map")
    config.add_route("map-data", "/map-data.json")
    config.add_route("node-details", r"/nodes/{id:\d+}")
    config.add_route("node-json", r"/nodes/{id:\d+}/json")
    config.add_route("node-preview", r"/nodes/{id:\d+}/preview")
    config.add_route("node-graphs", r"/nodes/{id:\d+}/graphs/{name}")
    config.add_route("nodes", "/nodes/{view}")
    config.add_route("network-errors", "/errors/{timestamp}")
    config.add_route("network-graphs", "/network/graphs/{name}")
    config.add_route(
        "link-graphs", r"/links/{source:\d+}-{destination:\d+}-{type}/graphs/{name}"
    )
    config.add_route(
        "link-preview", r"/links/{source:\d+}-{destination:\d+}-{type}/preview"
    )

    # Routes to generate individual graphs
    config.add_route("network-graph", r"/graphs/network/{name}")
    config.add_route("node-graph", r"/graphs/nodes/{id:\d+}/{name}")
    config.add_route(
        "link-graph", r"/graphs/links/{source:\d+}-{destination:\d+}-{type}/{name}"
    )
