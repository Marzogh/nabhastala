from __future__ import annotations

from datetime import UTC, date, datetime
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from paa.compute.ephemeris import (
    MOON_HORIZON_DEG,
    POINT_HORIZON_DEG,
    SUN_HORIZON_DEG,
    _body_events,
    _imports,
)
from paa.config import load_sites

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "output" / "_sources" / "occultations"

pytestmark = pytest.mark.skipif(
    not (SOURCE_ROOT / "de440s.bsp").is_file()
    or not (SOURCE_ROOT / "hip_main.dat").is_file(),
    reason="cached DE440s and Hipparcos sources are not available",
)


@pytest.fixture(scope="module")
def context():
    almanac, Star, load, load_file, wgs84, hipparcos, _names = _imports()
    ephemeris = load_file(str(SOURCE_ROOT / "de440s.bsp"))
    timescale = load.timescale()
    with (SOURCE_ROOT / "hip_main.dat").open("rb") as handle:
        stars = hipparcos.load_dataframe(handle)
    sites = {site.id: site for site in load_sites(ROOT / "config" / "sites.yaml")}
    return almanac, Star, ephemeris, timescale, wgs84, stars, sites


def _events(context, *, site_id: str, target, object_id: str, object_class: str, horizon: float):
    almanac, _Star, ephemeris, timescale, wgs84, _stars, sites = context
    site = sites[site_id]
    topos = wgs84.latlon(
        site.latitude_deg, site.longitude_deg, elevation_m=site.elevation_m
    )
    return _body_events(
        almanac=almanac,
        ephemeris=ephemeris,
        topos=topos,
        target=target,
        start=timescale.utc(2026, 1, 1),
        stop=timescale.utc(2027, 1, 1),
        timezone=ZoneInfo(site.timezone),
        object_class=object_class,
        object_id=object_id,
        object_name=object_id,
        horizon_degrees=horizon,
    )


def test_canopus_is_circumpolar_from_southern_tasmania(context) -> None:
    _almanac, Star, _ephemeris, _timescale, _wgs84, stars, _sites = context
    rows = _events(
        context,
        site_id="southern_tasmania",
        target=Star.from_dataframe(stars.loc[30438]),
        object_id="HIP 30438",
        object_class="star",
        horizon=POINT_HORIZON_DEG,
    )

    assert {row["event_type"] for row in rows} == {"upper_transit"}
    assert {row["horizon_state"] for row in rows} == {"always_above"}


@pytest.mark.parametrize("site_id", ["se_qld", "southern_tasmania"])
def test_polaris_does_not_rise_from_southern_sites(context, site_id: str) -> None:
    _almanac, Star, _ephemeris, _timescale, _wgs84, stars, _sites = context
    rows = _events(
        context,
        site_id=site_id,
        target=Star.from_dataframe(stars.loc[11767]),
        object_id="HIP 11767",
        object_class="star",
        horizon=POINT_HORIZON_DEG,
    )

    assert {row["event_type"] for row in rows} == {"upper_transit"}
    assert {row["horizon_state"] for row in rows} == {"always_below"}


def test_sirius_has_rise_transit_and_set_events(context) -> None:
    _almanac, Star, ephemeris, timescale, wgs84, stars, sites = context
    sirius = Star.from_dataframe(stars.loc[32349])
    rows = _events(
        context,
        site_id="se_qld",
        target=sirius,
        object_id="HIP 32349",
        object_class="star",
        horizon=POINT_HORIZON_DEG,
    )

    assert {row["event_type"] for row in rows} == {"rise", "upper_transit", "set"}
    horizon_rows = [row for row in rows if row["event_type"] in {"rise", "set"}]
    assert all(abs(float(row["altitude_deg"]) - POINT_HORIZON_DEG) <= 0.05 for row in horizon_rows)

    transit = next(row for row in rows if row["event_type"] == "upper_transit")
    moment = timescale.from_datetime(datetime.fromisoformat(str(transit["event_time_utc"])))
    site = sites["se_qld"]
    observer = ephemeris["earth"] + wgs84.latlon(
        site.latitude_deg, site.longitude_deg, elevation_m=site.elevation_m
    )
    right_ascension, _declination, _distance = (
        observer.at(moment).observe(sirius).apparent().radec(epoch="date")
    )
    local_sidereal_deg = (float(moment.gast) * 15 + site.longitude_deg) % 360
    hour_angle_deg = (
        local_sidereal_deg - float(right_ascension.hours) * 15 + 180
    ) % 360 - 180
    assert abs(hour_angle_deg) <= 0.02


def test_achernar_has_daily_rise_and_set_events(context) -> None:
    _almanac, Star, _ephemeris, _timescale, _wgs84, stars, _sites = context
    rows = _events(
        context,
        site_id="se_qld",
        target=Star.from_dataframe(stars.loc[7588]),
        object_id="HIP 7588",
        object_class="star",
        horizon=POINT_HORIZON_DEG,
    )

    for event_type in ("rise", "set"):
        moments = sorted(
            datetime.fromisoformat(str(row["event_time_utc"]))
            for row in rows
            if row["event_type"] == event_type
        )
        assert len(moments) >= 365
        assert max(
            later - earlier for earlier, later in pairwise(moments)
        ).total_seconds() < 26 * 3600


def test_some_civil_dates_have_no_moon_rise_or_set(context) -> None:
    _almanac, _Star, ephemeris, _timescale, _wgs84, _stars, _sites = context
    rows = _events(
        context,
        site_id="se_qld",
        target=ephemeris["moon"],
        object_id="moon",
        object_class="moon",
        horizon=MOON_HORIZON_DEG,
    )
    by_date: dict[str, set[str]] = {}
    for row in rows:
        by_date.setdefault(str(row["local_date"]), set()).add(str(row["event_type"]))

    missing = [
        day
        for day, event_types in by_date.items()
        if "rise" not in event_types or "set" not in event_types
    ]
    assert missing


def test_moon_rise_and_set_match_astral_to_the_minute(context) -> None:
    from astral import Observer
    from astral.moon import moonrise, moonset

    _almanac, _Star, ephemeris, _timescale, _wgs84, _stars, sites = context
    site = sites["se_qld"]
    rows = _events(
        context,
        site_id="se_qld",
        target=ephemeris["moon"],
        object_id="moon",
        object_class="moon",
        horizon=MOON_HORIZON_DEG,
    )
    selected = {
        row["event_type"]: datetime.fromisoformat(str(row["event_time_local"]))
        for row in rows
        if row["local_date"] == "2026-06-15" and row["event_type"] in {"rise", "set"}
    }
    observer = Observer(site.latitude_deg, site.longitude_deg, site.elevation_m)
    expected = {
        "rise": moonrise(observer, date=date(2026, 6, 15), tzinfo=site.timezone),
        "set": moonset(observer, date=date(2026, 6, 15), tzinfo=site.timezone),
    }

    assert set(selected) == {"rise", "set"}
    assert all(abs((selected[key] - expected[key]).total_seconds()) <= 90 for key in expected)


def test_sunrise_and_sunset_match_astral_to_the_minute(context) -> None:
    from astral import Observer
    from astral.sun import sunrise, sunset

    _almanac, _Star, ephemeris, _timescale, _wgs84, _stars, sites = context
    site = sites["se_qld"]
    rows = _events(
        context,
        site_id="se_qld",
        target=ephemeris["sun"],
        object_id="sun",
        object_class="sun",
        horizon=SUN_HORIZON_DEG,
    )
    selected = {
        row["event_type"]: datetime.fromisoformat(str(row["event_time_local"]))
        for row in rows
        if row["local_date"] == "2026-01-15" and row["event_type"] in {"rise", "set"}
    }
    observer = Observer(site.latitude_deg, site.longitude_deg, site.elevation_m)
    expected = {
        "rise": sunrise(observer, date=date(2026, 1, 15), tzinfo=site.timezone),
        "set": sunset(observer, date=date(2026, 1, 15), tzinfo=site.timezone),
    }

    assert set(selected) == {"rise", "set"}
    assert all(abs((selected[key] - expected[key]).total_seconds()) <= 90 for key in expected)


def test_saturn_transit_matches_astroplan_within_five_minutes(context) -> None:
    from astroplan import FixedTarget, Observer
    from astropy import units as u
    from astropy.coordinates import EarthLocation, get_body
    from astropy.time import Time

    _almanac, _Star, ephemeris, _timescale, _wgs84, _stars, sites = context
    site = sites["se_qld"]
    rows = _events(
        context,
        site_id="se_qld",
        target=ephemeris["saturn barycenter"],
        object_id="saturn",
        object_class="planet",
        horizon=POINT_HORIZON_DEG,
    )
    skyfield_transit = next(
        datetime.fromisoformat(str(row["event_time_utc"])).astimezone(UTC)
        for row in rows
        if row["event_type"] == "upper_transit"
        and row["event_time_utc"] >= "2026-06-01"
    )
    location = EarthLocation(
        lat=site.latitude_deg * u.deg,
        lon=site.longitude_deg * u.deg,
        height=site.elevation_m * u.m,
    )
    observer = Observer(location=location, timezone=site.timezone)
    reference_time = Time(skyfield_transit)
    target = FixedTarget(coord=get_body("saturn", reference_time, location))
    astroplan_transit = observer.target_meridian_transit_time(
        reference_time - 6 * u.hour, target, which="next"
    ).to_datetime(timezone=UTC)

    assert abs((skyfield_transit - astroplan_transit).total_seconds()) <= 300
