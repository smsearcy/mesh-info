import pytest


@pytest.mark.parametrize(
    "lat1, lon1, lat2, lon2, expected",
    [(42.939935, -122.147243, 42.956898, -122.050597, 8.089)],
)
def test_distance_calculation(lat1, lon1, lat2, lon2, expected):
    from meshinfo.collector import distance

    assert distance(lat1, lon1, lat2, lon2) == expected


@pytest.mark.parametrize(
    "lat1, lon1, lat2, lon2, expected",
    [(42.939935, -122.147243, 42.956898, -122.050597, 76.5)],
)
def test_bearing_calculation(lat1, lon1, lat2, lon2, expected):
    from meshinfo.collector import bearing

    assert bearing(lat1, lon1, lat2, lon2) == expected
