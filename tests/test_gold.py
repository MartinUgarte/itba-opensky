"""Tests de las agregaciones de gold (no necesitan Postgres)."""

from datetime import UTC, datetime

import pandas as pd

from opensky.gold import build_gold_tables

TS = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
T1 = pd.Timestamp("2026-11-12 10:00", tz="UTC")
T2 = pd.Timestamp("2026-11-12 10:05", tz="UTC")

# Silver de ejemplo: dos snapshots; e8044e aparece en los dos.
SILVER = pd.DataFrame(
    {
        "icao24": ["e8044e", "a1b2c3", "e8044e", "d4e5f6"],
        "callsign": ["ARG1234", None, "ARG1234", "TAM8001"],
        "origin_country": ["Argentina", "Argentina", "Argentina", "Brazil"],
        "snapshot_ts": [T1, T1, T2, T2],
        "baro_altitude": [1000.0, 50.0, 3000.0, 9000.0],
        "on_ground": [False, True, False, False],
        "velocity": [100.0, 0.0, 150.0, 250.0],
    }
)


def _tablas() -> dict[str, pd.DataFrame]:
    return build_gold_tables(SILVER, processed_ts=TS)


def test_genera_las_tres_tablas() -> None:
    assert set(_tablas()) == {
        "traffic_by_snapshot",
        "traffic_by_country",
        "aircraft_summary",
    }


def test_traffic_by_snapshot() -> None:
    gold = _tablas()["traffic_by_snapshot"]
    primero = gold.iloc[0]  # snapshot T1
    assert primero["aircraft"] == 2
    assert primero["on_ground"] == 1
    assert primero["airborne"] == 1
    assert primero["avg_altitude_m"] == 1000.0  # el avión en tierra no cuenta
    assert gold.iloc[1]["max_velocity_kmh"] == 250.0 * 3.6


def test_traffic_by_country() -> None:
    gold = _tablas()["traffic_by_country"]
    assert list(gold["origin_country"]) == [
        "Argentina",
        "Brazil",
    ]  # ordenado por aviones
    argentina = gold.iloc[0]
    assert argentina["aircraft"] == 2  # e8044e cuenta una sola vez
    assert argentina["observations"] == 3


def test_aircraft_summary() -> None:
    gold = _tablas()["aircraft_summary"].set_index("icao24")
    assert gold.loc["e8044e", "observations"] == 2
    assert gold.loc["e8044e", "first_seen"] == T1
    assert gold.loc["e8044e", "last_seen"] == T2
    assert gold.loc["e8044e", "max_altitude_m"] == 3000.0