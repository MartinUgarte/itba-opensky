"""Tests de las funciones de procesamiento de opensky.utils."""
 
import csv
from pathlib import Path
 
from opensky.utils import process_data, save_csv
 
# Respuesta de ejemplo de la API: solo nos importan las posiciones 0, 1 y 5 a 8.
DATA = {
    "states": [
        ["e8044e", "ARG1234 ", None, None, None, -58.5, -34.8, 1200.0, False],
        ["a1b2c3", None, None, None, None, -58.6, -34.9, None, True],
        ["4ca123", "   ", None, None, None, None, None, None, True],
    ]
}
 
 
def test_process_data_devuelve_un_avion_por_estado() -> None:
    aviones = process_data(DATA)
    assert len(aviones) == 3
    assert aviones[0]["icao24"] == "e8044e"
    assert aviones[0]["altitud_m"] == 1200.0
 
 
def test_process_data_limpia_el_callsign() -> None:
    aviones = process_data(DATA)
    assert aviones[0]["callsign"] == "ARG1234"
    assert aviones[1]["callsign"] is None
    assert aviones[2]["callsign"] is None
 
 
def test_process_data_sin_aviones_devuelve_lista_vacia() -> None:
    assert process_data({"states": None}) == []
 
 
def test_save_csv_escribe_un_archivo_con_los_aviones(tmp_path: Path) -> None:
    aviones = process_data(DATA)
 
    path = save_csv(aviones, carpeta=str(tmp_path))
 
    with path.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    assert len(filas) == 3
    assert filas[0]["icao24"] == "e8044e"