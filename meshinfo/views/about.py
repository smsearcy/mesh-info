from __future__ import annotations

from pyramid.request import Request
from pyramid.view import view_config


@view_config(route_name="about", renderer="pages/about.jinja2")
def about(request: Request):
    return {}
