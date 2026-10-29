import math

import pytest

from app.domain.geo import EARTH_RADIUS_MILES, haversine_miles, is_local, nearest_zip
from app.domain.models import LatLng

SOLDIER_FIELD = LatLng(41.8623, -87.6167)
LAMBEAU_FIELD = LatLng(44.5013, -88.0622)


def test_haversine_known_distance() -> None:
    # Reference value from a great-circle calculator: about 183 mi.
    assert haversine_miles(SOLDIER_FIELD, LAMBEAU_FIELD) == pytest.approx(183.3, abs=1.0)
    assert haversine_miles(SOLDIER_FIELD, SOLDIER_FIELD) == 0


def _point_at(miles: float) -> LatLng:
    # Due north: one degree of latitude is 2πR/360 miles.
    return LatLng(
        SOLDIER_FIELD.lat + miles / (EARTH_RADIUS_MILES * math.pi / 180), SOLDIER_FIELD.lng
    )


@pytest.mark.parametrize(("miles", "expected"), [(74.9, True), (74.999, True), (75.001, False)])
def test_is_local_boundary(miles: float, expected: bool) -> None:
    assert is_local(SOLDIER_FIELD, _point_at(miles), 75) is expected


def test_is_local_exactly_at_limit_is_local() -> None:
    venue = _point_at(75)
    assert is_local(SOLDIER_FIELD, venue, haversine_miles(SOLDIER_FIELD, venue)) is True


def test_is_local_unknown_venue_is_never_local() -> None:
    assert is_local(SOLDIER_FIELD, None, 75) is None


def test_nearest_zip() -> None:
    candidates = [("53202", LatLng(43.04, -87.90)), ("60601", LatLng(41.886, -87.62))]
    assert nearest_zip(LatLng(41.9, -87.63), candidates) == "60601"
    assert nearest_zip(LatLng(41.9, -87.63), []) is None


def test_nearest_zip_tie_takes_first() -> None:
    p = LatLng(40.0, -90.0)
    assert nearest_zip(LatLng(41.0, -90.0), [("a", LatLng(42.0, -90.0)), ("b", p)]) == "a"
