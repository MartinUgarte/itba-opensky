"""Capa bronze: guarda en Postgres los aviones que devuelve la API de OpenSky.

Usa la misma consulta de siempre (get_api, zona de Ezeiza) y guarda cada
state vector casi sin transformar. La limpieza queda para silver.
"""

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from opensky.constants import OPENSKY_URL
from opensky.utils import get_api

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://opensky:opensky@localhost:5432/datalake_prd"
)
SCHEMA = "opensky_bronze"
TABLE = "state_vectors"

# Posiciones del state vector de OpenSky (17 campos).
STATE_FIELDS = [
    "icao24",
    "callsign",
    "origin_country",
    "time_position",
    "last_contact",
    "longitude",
    "latitude",
    "baro_altitude",
    "on_ground",
    "velocity",
    "true_track",
    "vertical_rate",
    "sensors",
    "geo_altitude",
    "squawk",
    "spi",
    "position_source",
]

# Columnas de la tabla bronze y su tipo en pandas.
BRONZE_DTYPES: dict[str, Any] = {
    "icao24": "string",
    "callsign": "string",
    "origin_country": "string",
    "time_position": "Int64",
    "last_contact": "Int64",
    "longitude": "float",
    "latitude": "float",
    "baro_altitude": "float",
    "on_ground": "boolean",
    "velocity": "float",
    "true_track": "float",
    "vertical_rate": "float",
    "geo_altitude": "float",
    "squawk": "string",
    "position_source": "Int64",
    "raw_state_json": "string",
    "api_time": "Int64",
    "api_records_expected": "Int64",
    "run_id": "string",
    "ingestion_ts": "datetime64[us, UTC]",
}


def build_bronze_df(
    data: dict[str, Any], run_id: str, ingestion_ts: datetime
) -> pd.DataFrame:
    """Convierte la respuesta de la API en un DataFrame con el schema de bronze.

    Args:
        data: JSON devuelto por get_api ({"time": ..., "states": [...]}).
        run_id: Identificador de esta lectura de la API.
        ingestion_ts: Momento de escritura en bronze (UTC).

    Returns:
        Una fila por avión, con las columnas y tipos de BRONZE_DTYPES.
    """

    states: list[list[Any]] = data["states"] or [] 

    df = pd.DataFrame(states, columns=STATE_FIELDS)
    df["raw_state_json"] = [json.dumps(s) for s in states]
    df["api_time"] = data.get("time")
    df["api_records_expected"] = len(states)
    df["run_id"] = run_id
    df["ingestion_ts"] = ingestion_ts

    df = df.drop(columns=["sensors", "spi"])

    for columna, tipo in BRONZE_DTYPES.items():
        df[columna] = df[columna].astype(tipo)

    return df


def create_bronze_schema(engine: Engine) -> None:
    """Crea el schema de bronze si no existe. La tabla la crea to_sql."""
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

def load_bronze(df: pd.DataFrame, engine: Engine) -> int:
    """Agrega las filas a la tabla bronze."""
    with engine.begin() as conn:
        df.to_sql(
            TABLE, conn, schema=SCHEMA, if_exists="append", index=False, method="multi"
        )
    return len(df)


def main() -> None:
    """Consulta la API y guarda el resultado en bronze."""
    engine = create_engine(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))
    create_bronze_schema(engine)

    data = get_api(OPENSKY_URL)
    df = build_bronze_df(data, run_id=str(uuid.uuid4()), ingestion_ts=datetime.now(UTC))
    filas = load_bronze(df, engine)
    print(f"Insertadas {filas} filas en {SCHEMA}.{TABLE}")
