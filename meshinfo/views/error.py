import pendulum
from loguru import logger
from pyramid.view import exception_view_config


@exception_view_config(Exception, renderer="meshinfo:templates/500.jinja2")
def error_view(exc, request):
    request.response.status = 500
    logger.exception("Unhandled exception: {!r}", exc)
    return {
        "message": "Oops, something went wrong.",
        "timestamp": pendulum.now(),
    }
