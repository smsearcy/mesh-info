from pyramid.config import Configurator


def includeme(config: Configurator):
    config.add_static_view("static", "static", cache_max_age=3600)
    config.add_route("home", "/")
    config.add_route("nodes", "/nodes")
    config.add_route("node-details", r"/nodes/{id:\d+}")
    config.add_route("network-graphs", "/network/graphs/{name}")
    config.add_route("node-graphs", r"/nodes/{id:\d+}/graphs/{name}")
    config.add_route(
        "link-graphs", r"/links/{source:\d+}-{destination:\d+}/graphs/{name}"
    )

    # Routes to generate individual graphs
    config.add_route("network-graph", r"/graphs/network/{name}")
    config.add_route("node-graph", r"/graphs/nodes/{id:\d+}/{name}")
    config.add_route(
        "link-graph", r"/graphs/links/{source:\d+}-{destination:\d+}/{name}"
    )
