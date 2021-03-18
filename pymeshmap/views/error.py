from datetime import datetime

from loguru import logger
from pyramid.view import exception_view_config


@exception_view_config(Exception, renderer="pymeshmap:templates/500.mako")
def error_view(exc, request):
    request.response.status = 500
    logger.error("Unhandled exception: {!r}", exc)
    return {
        "message": "Oops, something went wrong.",
        "timestamp": datetime.now(),
    }
