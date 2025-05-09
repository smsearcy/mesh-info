from __future__ import annotations


def test_overview_success(testapp, dbsession):
    res = testapp.get("/", status=200)
    assert res.body


def test_nodes_success(testapp, dbsession):
    res = testapp.get("/nodes/table", status=200)
    assert res.body


def test_notfound(testapp):
    res = testapp.get("/badurl", status=404)
    assert res.status_code == 404
