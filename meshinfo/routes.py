from pyramid.config import Configurator


def includeme(config: Configurator):
    config.add_static_view("static", "static")
    config.add_route("home", "/")
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
