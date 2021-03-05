from pyramid.view import view_config

# from .. import models


@view_config(route_name="home", renderer="pymeshmap:templates/home.mako")
def overview(request):
    return {"project": "MeshMap"}
