from pyramid.request import Request
from pyramid.view import view_config


@view_config(route_name="about", renderer="meshinfo:templates/about.jinja2")
def about(request: Request):
    return {}
