"""Curated data files and gazetteer parsing (FR-O1a, FR-P3a)."""

from pathlib import Path

import pytest

from app.modules.schedule.centroids import clean_place_name, read_places
from app.modules.schedule.reference import (
    ReferenceDataError,
    load_overrides,
    load_rivalries,
)


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("Green Bay city", "Green Bay"),
        ("Landover CDP", "Landover"),
        ("East Rutherford borough", "East Rutherford"),
        ("Indianapolis city (balance)", "Indianapolis"),
        ("Nashville-Davidson metropolitan government (balance)", "Nashville-Davidson"),
        ("Orchard Park village", "Orchard Park"),
    ],
)
def test_clean_place_name(raw: str, clean: str) -> None:
    assert clean_place_name(raw) == clean


def test_read_places_prefers_incorporated_and_aliases_consolidated_cities(tmp_path: Path) -> None:
    gazetteer = tmp_path / "places.txt"
    gazetteer.write_text(
        "USPS|GEOID|GEOIDFQ|ANSICODE|NAME|LSAD|FUNCSTAT|ALAND|AWATER|ALAND_SQMI|AWATER_SQMI|"
        "INTPTLAT|INTPTLONG\n"
        "TN|1|x|x|Nashville-Davidson metropolitan government (balance)|00|F|1000|0|0|0|"
        "36.17|-86.78\n"
        "XX|2|x|x|Springfield CDP|57|S|9000|0|0|0|1.0|1.0\n"
        "XX|3|x|x|Springfield city|25|A|10|0|0|0|2.0|2.0\n"
    )
    places = {(p.name, p.state): p for p in read_places(gazetteer)}
    assert places[("Springfield", "XX")].lat == 2.0
    assert ("Nashville", "TN") in places and ("Nashville-Davidson", "TN") in places


def test_committed_overrides_and_rivalries_load() -> None:
    overrides = load_overrides()
    assert overrides.venue_cities["Green Bay"].state == "WI"
    london = overrides.venue_cities["London"]
    assert london.country == "GB" and london.lat is not None
    rivalries = load_rivalries()
    assert len(rivalries) == 10
    assert ("KC", "BUF", "Repeated high-stakes playoff meetings in recent seasons") in rivalries


def test_overrides_validation(tmp_path: Path) -> None:
    bad = tmp_path / "o.toml"
    bad.write_text('[venue_cities.Somewhere]\ncountry = "US"\n')
    with pytest.raises(ReferenceDataError, match="need a state"):
        load_overrides(bad)
    bad.write_text('[venue_cities.Paris]\ncountry = "FR"\n')
    with pytest.raises(ReferenceDataError, match="need lat and lng"):
        load_overrides(bad)
    bad.write_text('[teams.CHI]\ncolor = "navy"\n')
    with pytest.raises(ReferenceDataError, match="unknown override fields"):
        load_overrides(bad)


def test_rivalries_validation(tmp_path: Path) -> None:
    bad = tmp_path / "r.toml"
    bad.write_text('[[rivalry]]\nteams = ["KC", "KC"]\nreason = "x"\n')
    with pytest.raises(ReferenceDataError):
        load_rivalries(bad)
