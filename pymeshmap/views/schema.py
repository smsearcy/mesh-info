"""Input validation schemas/parsing for pyMeshMap views."""

import attr
import pendulum
from pyramid.httpexceptions import HTTPBadRequest


@attr.s(auto_attribs=True, slots=True)
class GraphParams:
    start: pendulum.DateTime
    end: pendulum.DateTime
    title: str = ""


def graph_params(params: dict) -> GraphParams:
    """Load graph parameters from request data dictionary."""
    end_time = pendulum.now()
    period = params.get("period", "day")

    if period == "day":
        start_time = end_time.subtract(days=1)
        title = "past day"
    elif period == "week":
        start_time = end_time.subtract(days=7)
        title = "past week"
    elif period == "month":
        start_time = end_time.subtract(months=1)
        title = "past month"
    elif period == "half-day":
        start_time = end_time.subtract(hours=12)
        title = "past 12 hours"
    else:
        raise HTTPBadRequest("Invalid period for graph")

    return GraphParams(
        start=start_time,
        end=end_time,
        title=title,
    )
