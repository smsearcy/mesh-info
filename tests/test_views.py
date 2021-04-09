from datetime import datetime, timezone

from pymeshmap import models
from pymeshmap.views.home import overview
from pymeshmap.views.notfound import notfound_view


def test_my_view_success(app_request, dbsession):
    stats = models.CollectorStat(
        started_at=datetime(2021, 4, 27, 11, 23, 35, tzinfo=timezone.utc),
        finished_at=datetime(2021, 4, 27, 11, 24, 35, tzinfo=timezone.utc),
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


def test_notfound_view(app_request):
    info = notfound_view(app_request)
    assert app_request.response.status_int == 404
    assert info == {}
