import pendulum
import structlog
from pyramid.view import exception_view_config

logger = structlog.get_logger()


@exception_view_config(Exception, renderer="pages/500.jinja2")
def error_view(exc, request):
    request.response.status = 500
    logger.exception("Unhandled exception", error=exc)
    return {
        "message": "Oops, something went wrong.",
        "timestamp": pendulum.now(),
    }
