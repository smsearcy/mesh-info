"""Input validation schemas/parsing for Mesh Info views."""

from __future__ import annotations

from pyramid.httpexceptions import HTTPBadRequest

from ..historical import GraphParams, Period


def graph_params(params: dict) -> GraphParams:
    """Load graph parameters from request data dictionary."""

    if "period" not in params:
        # TODO: handle arbitrary dates...
        raise HTTPBadRequest("Must specify period for graph")

    try:
        period = getattr(Period, params["period"].upper())
    except KeyError as err:
        raise HTTPBadRequest("Invalid period for graph") from err
    title = f"past {params['period'].lower()}"

    return GraphParams(
        period=period,
        title=title,
    )
