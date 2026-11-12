"""Tests de la transformación a silver (no necesitan Postgres)."""

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from opensky.bronze import build_bronze_df
from opensky.silver import SILVER_DTYPES, build_silver_df

TS = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)

DATA: dict[str, Any] = {
    "time": 1789000000,
    "states": [
        [
            "E8044E",
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
            "        ",
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
            2,
        ],
        [
            "ffffff",
            "SINPOS  ",
            "Brazil",
            None,
            1788999900,
            None,
            None,
            None,
            False,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            0,
        ],
    ],
}


def _bronze() -> pd.DataFrame:
    return build_bronze_df(DATA, run_id="run-1", ingestion_ts=TS)


def test_columnas_de_silver() -> None:
    silver = build_silver_df(_bronze(), processed_ts=TS)
    assert list(silver.columns) == list(SILVER_DTYPES)


def test_limpia_textos() -> None:
    silver = build_silver_df(_bronze(), processed_ts=TS)
    assert silver.loc[0, "icao24"] == "e8044e"
    assert silver.loc[0, "callsign"] == "ARG1234"
    assert silver["callsign"].isna().iloc[1]  # callsign vacío -> nulo


def test_convierte_epochs_y_codigos() -> None:
    silver = build_silver_df(_bronze(), processed_ts=TS)
    assert silver.loc[0, "snapshot_ts"] == pd.Timestamp(1789000000, unit="s", tz="UTC")
    assert silver["position_ts"].isna().iloc[1]
    assert list(silver["position_source"]) == ["ADS-B", "MLAT"]


def test_descarta_aviones_sin_posicion() -> None:
    silver = build_silver_df(_bronze(), processed_ts=TS)
    assert "ffffff" not in set(silver["icao24"])


def test_deduplica_el_mismo_snapshot() -> None:
    otra_carga = build_bronze_df(DATA, run_id="run-2", ingestion_ts=datetime.now(UTC))
    bronze = pd.concat([_bronze(), otra_carga], ignore_index=True)
    silver = build_silver_df(bronze, processed_ts=TS)
    assert len(silver) == 2
    assert set(silver["run_id"]) == {"run-2"}  # se queda con la última carga