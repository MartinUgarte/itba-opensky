"""Consulta a la API de OpenSky y procesamiento de los datos."""

import csv
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

import requests

from opensky.constants import (
    EZE_LAT_MAX,
    EZE_LAT_MIN,
    EZE_LON_MAX,
    EZE_LON_MIN,
    INITIAL_WAIT,
    TRIES,
)


class OpenSkyError(Exception):
    """La API de OpenSky no respondió después de los reintentos."""


class Avion(TypedDict):
    """Un avión cerca de Ezeiza, con nombres claros.

    Attributes
    ----------
    icao24 : str
        Identificador único del transpondedor del avión.
    callsign : str or None
        Código del vuelo, por ejemplo "ARG1234", o None si no lo informa.
    longitud : float or None
        Longitud en grados, o None si no informa posición.
    latitud : float or None
        Latitud en grados, o None si no informa posición.
    altitud_m : float or None
        Altitud barométrica en metros, o None si el avión
        está en tierra y no informa altitud.
    en_tierra : bool
        True si el avión está en la superficie.
    """

    icao24: str
    callsign: str | None
    longitud: float | None
    latitud: float | None
    altitud_m: float | None
    en_tierra: bool


def get_api(url: str) -> dict[str, Any]:
    """Consulta el estado de los aviones en la zona de Ezeiza.

    Args:
        url: URL del endpoint states/all de OpenSky.

    Returns:
        La respuesta de la API como diccionario.

    Raises:
        requests.RequestException: Si no se pudo conectar o la API respondió con error.
    """
    print("Consultando la API de OpenSky")
    params = {
        "lamin": EZE_LAT_MIN,
        "lomin": EZE_LON_MIN,
        "lamax": EZE_LAT_MAX,
        "lomax": EZE_LON_MAX,
    }
    for intento in range(1, TRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            break  # salió bien: salimos del for
        except requests.RequestException as e:
            if intento == TRIES:
                raise OpenSkyError(
                    f"No se pudo consultar la API de OpenSky después de {TRIES} intentos: {e}"
                ) from e
            espera = INITIAL_WAIT * 2 ** (intento - 1)
            print(f"Intento {intento} falló ({e}). Reintento en {espera} s...")
            time.sleep(espera)

    data: dict[str, Any] = r.json()
    return data


def process_data(data: dict[str, Any]) -> list[Avion]:
    """Convierte la respuesta de la API en una lista de aviones con nombres claros.

    Args:
        data: La respuesta de la API, con la lista de aviones en "states".

    Returns:
        Un diccionario por avión. Lista vacía si no hay aviones en la zona.
    """
    states = data["states"] or []  # la API devuelve null si no hay aviones
    aviones = []
    for avion in states:
        aviones.append(
            {
                "icao24": avion[0],  # Id del avión
                "callsign": (avion[1] or "").strip() or None,  # Código de vuelo
                "longitud": avion[5],
                "latitud": avion[6],
                "altitud_m": avion[7],
                "en_tierra": avion[8],
            }
        )
    return aviones


def save_csv(aviones: list[Avion], carpeta: str = "data") -> Path:
    """Guarda los aviones en un CSV nuevo, con la fecha y hora en el nombre.

    Parameters
    ----------
    aviones : list[Avion]
        Aviones a guardar.
    carpeta : str, optional
        Carpeta de destino; se crea si no existe. Por defecto "data".

    Returns
    -------
    Path
        La ruta del archivo escrito.
    """
    destino = Path(carpeta)
    destino.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = destino / f"aviones_{ts}.csv"

    columnas = list(Avion.__annotations__)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(aviones)

    return path
