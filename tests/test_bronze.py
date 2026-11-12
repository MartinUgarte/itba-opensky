"""Tests de la transformación a bronze (no necesitan Postgres)."""

import json
from datetime import UTC, datetime
from typing import Any

from opensky.bronze import BRONZE_COLUMNS, build_bronze_df

TS = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)

DATA: dict[str, Any] = {
    "time": 1789000000,
    "states": [
        [
            "e8044e",
            "ARG1234 ",
            "Argentina",
            1788999990,
            1788999995,
            -58.5,
            -34.8,
            1200.0,
            False,
            80.5,
            270.0,
            -3.2,
            None,
            1250.0,
            "1234",
            False,
            0,
        ],
        [
            "a1b2c3",
            None,
            "Argentina",
            None,
            1788999900,
            -58.6,
            -34.9,
            None,
            True,
            0.0,
            0.0,
            None,
            None,
            None,
            None,
            False,
            0,
        ],
    ],
}


def test_columnas_y_tipos_de_bronze() -> None:
    df = build_bronze_df(DATA, run_id="run-1", ingestion_ts=TS)
    assert list(df.columns) == list(BRONZE_COLUMNS)
    assert str(df["time_position"].dtype) == "Int64"
    assert str(df["on_ground"].dtype) == "boolean"


def test_bronze_no_transforma_los_datos() -> None:
    df = build_bronze_df(DATA, run_id="run-1", ingestion_ts=TS)
    assert df.loc[0, "callsign"] == "ARG1234 "  # con el espacio de relleno
    assert json.loads(str(df.loc[0, "raw_state_json"])) == DATA["states"][0]
    assert df["baro_altitude"].isna().iloc[1]


def test_metadatos_de_la_lectura() -> None:
    df = build_bronze_df(DATA, run_id="run-1", ingestion_ts=TS)
    assert (df["api_records_expected"] == 2).all()
    assert (df["api_time"] == 1789000000).all()
    assert (df["run_id"] == "run-1").all()


def test_sin_aviones_devuelve_df_vacio_con_schema() -> None:
    df = build_bronze_df(
        {"time": 1789000000, "states": None}, run_id="run-1", ingestion_ts=TS
    )
    assert df.empty
    assert list(df.columns) == list(BRONZE_COLUMNS)
