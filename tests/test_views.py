import pendulum

from meshinfo import models
from meshinfo.views.home import overview
from meshinfo.views.nodes import NodeListViews
from meshinfo.views.notfound import notfound_view

# TODO: Create a unified set of demo/test data


def test_overview_view_success(app_request, dbsession):
    stats = models.CollectorStat(
        started_at=pendulum.datetime(2021, 4, 27, 11, 23, 35, tz="UTC"),
        finished_at=pendulum.datetime(2021, 4, 27, 11, 24, 35, tz="UTC"),
        node_count=24,
        link_count=80,
        error_count=1,
        polling_duration=45.45,
        total_duration=60,
        other_stats={},
    )
    dbsession.add(stats)
    dbsession.flush()

    info = overview(app_request)
    assert app_request.response.status_int == 200
    assert info["node_count"] == 0
    assert info["link_count"] == 0
    assert info["last_run"] == stats


def test_nodes_view_success(app_request, dbsession):
    info = NodeListViews(app_request).table()
    assert app_request.response.status_int == 200
    assert len(info["nodes"]) == 0


def test_notfound_view(app_request):
    info = notfound_view(app_request)
    assert app_request.response.status_int == 404
    assert info == {"message": "Sorry, the specified page does not exist."}
