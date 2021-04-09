def test_my_view_success(testapp, dbsession):
    res = testapp.get("/", status=200)
    assert res.body


def test_notfound(testapp):
    res = testapp.get("/badurl", status=404)
    assert res.status_code == 404
