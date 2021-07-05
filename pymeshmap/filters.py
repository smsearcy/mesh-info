"""Filter for Jinja templates."""

import jinja2
from pyramid.threadlocal import get_current_request


def duration(value):
    if value > 120:
        return f"{value / 60:.2f}m"
    else:
        return f"{value:.2f}s"


def in_tz(dt, tz="utc"):
    if tz == "server":
        tz = "local"
    return dt.in_tz(tz).format("YYYY-MM-DD HH:mm:ss zz")


@jinja2.pass_context
def local_tz(ctx, dt):
    request = ctx.get("request") or get_current_request()
    return dt.in_tz(request.timezone).format("YYYY-MM-DD HH:mm:ss zz")
