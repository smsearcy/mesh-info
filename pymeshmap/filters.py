"""Filter for Jinja templates."""

import jinja2
from pyramid.threadlocal import get_current_request


def duration(value):
    if value > 120:
        return f"{value / 60}m"
    else:
        return f"{value}s"


def timestamp(dt):
    return dt.in_tz("utc").format("YYYY-MM-DD HH:mm:ss zz")


@jinja2.pass_context
def local_tz(ctx, dt):
    request = ctx.get("request") or get_current_request()
    return dt.in_tz(request.timezone).format("YYYY-MM-DD HH:mm:ss zz")
