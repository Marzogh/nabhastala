from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from io import StringIO

import requests


API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"


@dataclass(frozen=True)
class HorizonsSite:
    latitude_deg: float
    longitude_deg: float
    elevation_m: float


@dataclass(frozen=True)
class HorizonsQuery:
    command: str
    start_utc: datetime
    stop_utc: datetime
    step_minutes: int
    site: HorizonsSite
    quantities: str = "1"


def parse_horizons_csv(raw: str) -> list[list[str]]:
    start = raw.find("$$SOE")
    end = raw.find("$$EOE")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Horizons output missing $$SOE/$$EOE data block")
    lines = [line.strip() for line in raw[start + len("$$SOE") : end].strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("Horizons data block is empty")
    return [line.split(",") for line in lines]


def fetch_observer_ephemeris(query: HorizonsQuery) -> str:
    params = {
        "format": "text",
        "COMMAND": f"'{query.command}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'coord@399'",
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{query.site.longitude_deg},{query.site.latitude_deg},{query.site.elevation_m / 1000.0}'",
        "START_TIME": f"'{query.start_utc.strftime('%Y-%m-%d %H:%M')}'",
        "STOP_TIME": f"'{query.stop_utc.strftime('%Y-%m-%d %H:%M')}'",
        "STEP_SIZE": f"'{query.step_minutes} m'",
        "QUANTITIES": f"'{query.quantities}'",
        "ANG_FORMAT": "'DEG'",
        "CSV_FORMAT": "'YES'",
    }
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.text


def parse_horizons_observer_ra_dec(raw: str) -> list[dict]:
    lines = raw.splitlines()
    try:
        soe = next(i for i, line in enumerate(lines) if line.strip() == "$$SOE")
        eoe = next(i for i, line in enumerate(lines) if line.strip() == "$$EOE")
    except StopIteration as exc:
        raise ValueError("Horizons output missing $$SOE/$$EOE") from exc

    header_line = None
    for i in range(soe - 1, -1, -1):
        if "Date__(UT)__HR:MN" in lines[i]:
            header_line = lines[i]
            break
    if header_line is None:
        raise ValueError("Could not find Horizons CSV header")

    headers = [h.strip() for h in next(csv.reader([header_line]))]
    rows = [line for line in lines[soe + 1 : eoe] if line.strip()]
    data = list(csv.reader(StringIO("\n".join(rows))))

    def _find_col(candidates: list[str]) -> int:
        for idx, h in enumerate(headers):
            hl = h.lower()
            if any(c in hl for c in candidates):
                return idx
        raise ValueError(f"Missing column for candidates {candidates}")

    date_col = _find_col(["date__(ut)"])
    ra_col = _find_col(["r.a.", "ra"])
    dec_col = _find_col(["dec"])

    out: list[dict] = []
    for row in data:
        if len(row) <= max(date_col, ra_col, dec_col):
            continue
        dt = datetime.strptime(row[date_col].strip(), "%Y-%b-%d %H:%M")
        out.append(
            {
                "datetime_utc": dt,
                "ra_deg": float(row[ra_col].strip()),
                "dec_deg": float(row[dec_col].strip()),
            }
        )
    return out


def parse_horizons_observer_quantities(raw: str) -> list[dict]:
    lines = raw.splitlines()
    try:
        soe = next(i for i, line in enumerate(lines) if line.strip() == "$$SOE")
        eoe = next(i for i, line in enumerate(lines) if line.strip() == "$$EOE")
    except StopIteration as exc:
        raise ValueError("Horizons output missing $$SOE/$$EOE") from exc

    header_line = None
    for i in range(soe - 1, -1, -1):
        if "Date__(UT)__HR:MN" in lines[i]:
            header_line = lines[i]
            break
    if header_line is None:
        raise ValueError("Could not find Horizons CSV header")

    headers = [h.strip() for h in next(csv.reader([header_line]))]
    rows = [line for line in lines[soe + 1 : eoe] if line.strip()]
    data = list(csv.reader(StringIO("\n".join(rows))))

    def _find_col(candidates: list[str]) -> int:
        for idx, h in enumerate(headers):
            hl = h.lower()
            if any(c in hl for c in candidates):
                return idx
        raise ValueError(f"Missing column for candidates {candidates}")

    date_col = _find_col(["date__(ut)"])
    elev_col = _find_col(["elev_"])
    mag_col = _find_col(["apmag"])
    sot_col = _find_col(["s-o-t"])

    out: list[dict] = []
    for row in data:
        if len(row) <= max(date_col, elev_col, mag_col, sot_col):
            continue
        dt = datetime.strptime(row[date_col].strip(), "%Y-%b-%d %H:%M")
        out.append(
            {
                "datetime_utc": dt,
                "elevation_deg": float(row[elev_col].strip()),
                "apmag": float(row[mag_col].strip()),
                "solar_elong_deg": float(row[sot_col].strip()),
            }
        )
    return out
