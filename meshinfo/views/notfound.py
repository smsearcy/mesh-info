from pyramid.request import Request
from pyramid.view import notfound_view_config


@notfound_view_config(renderer="meshinfo:templates/404.jinja2")
def notfound_view(request: Request):
    request.response.status = 404
    if request.matched_route is not None:
        # presumably we raised this exception so return the message
        message = request.exception.message
    else:
        message = "Sorry, the specified page does not exist."
    return {"message": message}
