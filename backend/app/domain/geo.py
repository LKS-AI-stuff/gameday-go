"""Distances and nearest points (BRD A5, FR-P3). Pure functions."""

import math
from collections.abc import Sequence

from app.domain.models import LatLng

EARTH_RADIUS_MILES = 3958.8


def haversine_miles(a: LatLng, b: LatLng) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlng = math.radians(b.lng - a.lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(min(1.0, math.sqrt(h)))


def is_local(home: LatLng, venue: LatLng | None, local_miles: float) -> bool | None:
    """Within the local area (75 mi by default). Unknown venue → None, never local."""
    if venue is None:
        return None
    return haversine_miles(home, venue) <= local_miles


def nearest_zip[K](point: LatLng, candidates: Sequence[tuple[K, LatLng]]) -> K | None:
    """Key of the closest candidate (first one on a tie), or None when there are none.

    Generic over the key: "Use my location" finds a ZIP, and seeding finds each ZIP's place.
    """
    best: K | None = None
    best_distance = math.inf
    for key, location in candidates:
        distance = haversine_miles(point, location)
        if distance < best_distance:
            best, best_distance = key, distance
    return best
