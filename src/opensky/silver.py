"""Capa silver: limpia los datos de bronze y los deja listos para analizar.

Lee toda la tabla de bronze, aplica las transformaciones y reescribe la
tabla de silver completa en cada corrida.
"""

import os
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from opensky.bronze import DEFAULT_DATABASE_URL
from opensky.bronze import SCHEMA as BRONZE_SCHEMA
from opensky.bronze import TABLE as BRONZE_TABLE

SCHEMA = "opensky_silver"
TABLE = "state_vectors"

# Códigos de position_source según la documentación de OpenSky.
POSITION_SOURCES = {0: "ADS-B", 1: "ASTERIX", 2: "MLAT", 3: "FLARM"}

# Columnas de la tabla silver y su tipo en pandas.
SILVER_DTYPES: dict[str, Any] = {
    "icao24": "string",
    "callsign": "string",
    "origin_country": "string",
    "snapshot_ts": "datetime64[us, UTC]",
    "position_ts": "datetime64[us, UTC]",
    "last_contact_ts": "datetime64[us, UTC]",
    "latitude": "float",
    "longitude": "float",
    "baro_altitude": "float",
    "geo_altitude": "float",
    "on_ground": "boolean",
    "velocity": "float",
    "true_track": "float",
    "vertical_rate": "float",
    "squawk": "string",
    "position_source": "string",
    "run_id": "string",
    "ingestion_ts": "datetime64[us, UTC]",
    "processed_ts": "datetime64[us, UTC]",
}


def read_bronze(engine: Engine) -> pd.DataFrame:
    """Lee la tabla de bronze completa."""
    return pd.read_sql_table(BRONZE_TABLE, engine, schema=BRONZE_SCHEMA)


def build_silver_df(bronze: pd.DataFrame, processed_ts: datetime) -> pd.DataFrame:
    """Limpia los datos de bronze.

    Args:
        bronze: Filas de la tabla de bronze.
        processed_ts: Momento en que se procesa silver (UTC).

    Returns:
        Una fila por avión y snapshot, con las columnas y tipos de SILVER_DTYPES.
    """
    
    # Sin posición no sirve para analizar: se descarta.
    df = bronze.dropna(subset=["latitude", "longitude"])

    # Textos: sacar espacios de relleno; callsign vacío pasa a nulo.
    df["icao24"] = df["icao24"].str.strip().str.lower()
    df["callsign"] = df["callsign"].str.strip()
    df.loc[df["callsign"] == "", "callsign"] = pd.NA

    # Epochs (segundos) a timestamps UTC.
    df["snapshot_ts"] = pd.to_datetime(df["api_time"], unit="s", utc=True)
    df["position_ts"] = pd.to_datetime(df["time_position"], unit="s", utc=True)
    df["last_contact_ts"] = pd.to_datetime(df["last_contact"], unit="s", utc=True)

    # Código numérico a nombre legible (0 -> "ADS-B").
    df["position_source"] = df["position_source"].map(POSITION_SOURCES)

    # Si el mismo snapshot se cargó dos veces en bronze, nos quedamos con la última carga.
    df = df.sort_values("ingestion_ts")
    df = df.drop_duplicates(subset=["icao24", "snapshot_ts"], keep="last")

    df["processed_ts"] = processed_ts

    df = df[list(SILVER_DTYPES)]
    for columna, tipo in SILVER_DTYPES.items():
        df[columna] = df[columna].astype(tipo)

    return df.reset_index(drop=True)


def create_silver_schema(engine: Engine) -> None:
    """Crea el schema de silver si no existe. La tabla la crea to_sql."""
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))


def load_silver(df: pd.DataFrame, engine: Engine) -> int:
    """Reemplaza la tabla de silver con las filas nuevas."""
    with engine.begin() as conn:
        df.to_sql(
            TABLE, conn, schema=SCHEMA, if_exists="replace", index=False, method="multi"
        )
    return len(df)


def main() -> None:
    """Lee bronze, lo limpia y guarda el resultado en silver."""
    engine = create_engine(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))
    create_silver_schema(engine)

    bronze = read_bronze(engine)
    df = build_silver_df(bronze, processed_ts=datetime.now(UTC))
    filas = load_silver(df, engine)
    print(
        f"Leídas {len(bronze)} filas de bronze, insertadas {filas} en {SCHEMA}.{TABLE}"
    )