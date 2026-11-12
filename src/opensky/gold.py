"""Capa gold: métricas agregadas a partir de silver, listas para consumir.

Arma tres tablas con groupby y reescribe cada una completa en cada corrida:
- traffic_by_snapshot: cuántos aviones había en cada snapshot.
- traffic_by_country: aviones por país de matrícula.
- aircraft_summary: un resumen por avión.
"""

import os
from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from opensky.bronze import DEFAULT_DATABASE_URL
from opensky.silver import SCHEMA as SILVER_SCHEMA
from opensky.silver import TABLE as SILVER_TABLE

SCHEMA = "opensky_gold"

MS_TO_KMH = 3.6  # 1 m/s = 3.6 km/h


def read_silver(engine: Engine) -> pd.DataFrame:
    """Lee la tabla de silver completa."""
    return pd.read_sql_table(SILVER_TABLE, engine, schema=SILVER_SCHEMA)


def prepare(silver: pd.DataFrame) -> pd.DataFrame:
    """Agrega las columnas derivadas que usan las tablas de gold."""
    df = silver.copy()
    df["velocity_kmh"] = df["velocity"] * MS_TO_KMH
    # Altitud solo de los aviones en vuelo: en tierra queda nula y no cuenta en el promedio.
    df["airborne_altitude"] = df["baro_altitude"].where(~df["on_ground"])
    return df


def traffic_by_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por snapshot: cuántos aviones había, en tierra y en vuelo."""
    gold = df.groupby("snapshot_ts", as_index=False).agg(
        aircraft=("icao24", "nunique"),
        on_ground=("on_ground", "sum"),
        avg_altitude_m=("airborne_altitude", "mean"),
        max_velocity_kmh=("velocity_kmh", "max"),
    )
    gold["airborne"] = gold["aircraft"] - gold["on_ground"]
    columnas = [
        "snapshot_ts",
        "aircraft",
        "on_ground",
        "airborne",
        "avg_altitude_m",
        "max_velocity_kmh",
    ]
    return gold[columnas].sort_values("snapshot_ts").reset_index(drop=True)


def traffic_by_country(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por país de matrícula, de mayor a menor cantidad de aviones."""
    gold = df.groupby("origin_country", as_index=False).agg(
        aircraft=("icao24", "nunique"),
        observations=("icao24", "size"),
        avg_velocity_kmh=("velocity_kmh", "mean"),
        first_seen=("snapshot_ts", "min"),
        last_seen=("snapshot_ts", "max"),
    )
    return gold.sort_values("aircraft", ascending=False).reset_index(drop=True)


def aircraft_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por avión: cuándo se lo vio y sus máximos."""
    df = df.sort_values("snapshot_ts")  # para que "last" sea el callsign más reciente
    gold = df.groupby("icao24", as_index=False).agg(
        callsign=("callsign", "last"),
        origin_country=("origin_country", "first"),
        observations=("snapshot_ts", "size"),
        first_seen=("snapshot_ts", "min"),
        last_seen=("snapshot_ts", "max"),
        max_altitude_m=("baro_altitude", "max"),
        max_velocity_kmh=("velocity_kmh", "max"),
    )
    return gold.sort_values("observations", ascending=False).reset_index(drop=True)


def build_gold_tables(
    silver: pd.DataFrame, processed_ts: datetime
) -> dict[str, pd.DataFrame]:
    """Arma todas las tablas de gold: nombre de la tabla -> DataFrame."""
    df = prepare(silver)
    tablas = {
        "traffic_by_snapshot": traffic_by_snapshot(df),
        "traffic_by_country": traffic_by_country(df),
        "aircraft_summary": aircraft_summary(df),
    }
    for gold in tablas.values():
        gold["processed_ts"] = processed_ts
    return tablas


def create_gold_schema(engine: Engine) -> None:
    """Crea el schema de gold si no existe. Las tablas las crea to_sql."""
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))


def load_gold(tablas: dict[str, pd.DataFrame], engine: Engine) -> None:
    """Reemplaza cada tabla de gold con sus filas nuevas."""
    with engine.begin() as conn:
        for nombre, gold in tablas.items():
            gold.to_sql(
                nombre,
                conn,
                schema=SCHEMA,
                if_exists="replace",
                index=False,
                method="multi",
            )


def main() -> None:
    """Lee silver, arma las agregaciones y las guarda en gold."""
    engine = create_engine(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))
    create_gold_schema(engine)

    silver = read_silver(engine)
    tablas = build_gold_tables(silver, processed_ts=datetime.now(UTC))
    load_gold(tablas, engine)
    for nombre, gold in tablas.items():
        print(f"Insertadas {len(gold)} filas en {SCHEMA}.{nombre}")