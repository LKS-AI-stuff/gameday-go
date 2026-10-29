"""Builds the committed ZIP and place coordinate files from the Census gazetteers (FR-P3a, D11).

Run once per gazetteer release: `uv run python -m app.cli build-centroids <zcta.txt> <place.txt>`.
The raw gazetteer files (public domain, census.gov) aren't committed.
"""

import csv
import math
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path

from app.domain.geo import haversine_miles
from app.domain.models import LatLng

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
ZIP_FILE = DATA_DIR / "zip_centroids.csv"
PLACE_FILE = DATA_DIR / "place_centroids.csv"

# Legal/statistical descriptors the gazetteer appends to place names ("Green Bay city").
_DESCRIPTOR = re.compile(
    r"\s+(?:city and borough|consolidated government|metropolitan government|metro government"
    r"|unified government|urban county|zona urbana|comunidad|municipality|borough|village"
    r"|town|city|CDP|plantation|corporation|township)$"
)
_BALANCE = re.compile(r"\s*\(balance\)$")


def clean_place_name(raw: str) -> str:
    """'Indianapolis city (balance)' → 'Indianapolis'; 'Green Bay city' → 'Green Bay'."""
    return _DESCRIPTOR.sub("", _BALANCE.sub("", raw.strip())).strip()


METERS_PER_MILE = 1609.344


@dataclass(frozen=True)
class Place:
    name: str
    state: str
    lat: float
    lng: float
    # Radius of a circle with the place's land area: a ZIP inside a big city's footprint
    # belongs to it even when a small neighbor's center is closer (10001 is New York, not Hoboken).
    radius_miles: float = 0.0


def _rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        sample = f.readline()
        f.seek(0)
        delimiter = "|" if "|" in sample else "\t"
        for row in csv.DictReader(f, delimiter=delimiter):
            yield {k.strip(): (v or "").strip() for k, v in row.items() if k}


def read_places(path: Path) -> list[Place]:
    """One place per (name, state): incorporated places win over CDPs, then larger land area.

    Consolidated cities also get their common name ("Nashville-Davidson" → "Nashville"),
    unless another place in the state already has it.
    """
    best: dict[tuple[str, str], tuple[tuple[bool, float], Place]] = {}
    aliases: list[tuple[tuple[bool, float], Place]] = []
    for row in _rows(path):
        name = clean_place_name(row["NAME"])
        land = float(row.get("ALAND") or 0)
        place = Place(
            name,
            row["USPS"],
            float(row["INTPTLAT"]),
            float(row["INTPTLONG"]),
            math.sqrt(land / math.pi) / METERS_PER_MILE,
        )
        rank = (row.get("FUNCSTAT") == "A", land)
        key = (name, place.state)
        if key not in best or rank > best[key][0]:
            best[key] = (rank, place)
        if _BALANCE.search(row["NAME"]):
            common = re.split(r"[-/]", name)[0].strip()
            if common != name:
                aliases.append((rank, replace(place, name=common)))
    for rank, alias in aliases:
        best.setdefault((alias.name, alias.state), (rank, alias))
    return sorted((p for _, p in best.values()), key=lambda p: (p.state, p.name))


class _Grid:
    """1-degree buckets, so each ZIP compares against nearby places only."""

    def __init__(self, places: Iterable[Place]) -> None:
        self._cells: dict[tuple[int, int], list[Place]] = defaultdict(list)
        for place in places:
            self._cells[self._cell(place.lat, place.lng)].append(place)

    @staticmethod
    def _cell(lat: float, lng: float) -> tuple[int, int]:
        return math.floor(lat), math.floor(lng)

    def nearest(self, point: LatLng) -> Place | None:
        cy, cx = self._cell(point.lat, point.lng)
        for radius in (1, 2, 4):
            candidates = [
                p
                for dy in range(-radius, radius + 1)
                for dx in range(-radius, radius + 1)
                for p in self._cells.get((cy + dy, cx + dx), [])
            ]
            if candidates:
                return min(
                    candidates,
                    key=lambda p: haversine_miles(point, LatLng(p.lat, p.lng)) - p.radius_miles,
                )
        return None


def build(zcta_path: Path, places_path: Path, out_dir: Path = DATA_DIR) -> tuple[int, int]:
    places = read_places(places_path)
    grid = _Grid(places)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / PLACE_FILE.name).open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "state", "lat", "lng"])
        for p in places:
            writer.writerow([p.name, p.state, p.lat, p.lng])

    zips = 0
    with (out_dir / ZIP_FILE.name).open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["zip", "lat", "lng", "place_name", "state"])
        for row in _rows(zcta_path):
            point = LatLng(float(row["INTPTLAT"]), float(row["INTPTLONG"]))
            place = grid.nearest(point)
            if place is None:
                continue
            writer.writerow([row["GEOID"], point.lat, point.lng, place.name, place.state])
            zips += 1
    return zips, len(places)
