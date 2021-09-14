from pyramid.config import Configurator


def includeme(config: Configurator):
    config.add_static_view("static", "static", cache_max_age=3600)
    config.add_route("home", "/")
    config.add_route("nodes", "/nodes")
    config.add_route("node", r"/nodes/{id:\d+}")
    config.add_route(
        "link-graph", r"/links/{source:\d+}-{destination:\d+}-{type}/graphs/{name}"
    )
    config.add_route("node-graph", r"/nodes/{id:\d+}/graphs/{name}")
    # TODO: make a page that lists all the graphs?
    # config.add_route("node-graphs", r"/nodes/{id:\d+}/graphs")
    config.add_route("network-graph", r"/network/graphs/{name}")
