from datetime import datetime

from pyramid.httpexceptions import HTTPServerError
from pyramid.view import exception_view_config


@exception_view_config(HTTPServerError, renderer="pymeshmap:templates/500.mako")
def error_view(request):
    request.response.status = 500
    return {"timestamp": datetime.now()}
