"""Filter for Jinja templates."""

from __future__ import annotations

import jinja2
from pyramid.threadlocal import get_current_request


def duration(value):
    if value > 120:
        return f"{value / 60:.2f}m"
    return f"{value:.2f}s"


def in_tz(dt, tz="utc"):
    if tz == "server":
        tz = "local"
    return dt.in_tz(tz).format("YYYY-MM-DD HH:mm:ss zz")


@jinja2.pass_context
def local_tz(ctx, dt):
    request = ctx.get("request") or get_current_request()
    return dt.in_tz(request.timezone).format("YYYY-MM-DD HH:mm:ss zz")


def unknown(value, places: int = 2):
    if value is None:
        return "Unknown"
    if isinstance(value, float):
        return f"{value:.{places}f}"
    return value
