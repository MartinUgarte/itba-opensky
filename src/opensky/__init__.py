"""opensky: estado actual de los aviones cerca de Ezeiza."""

from opensky.constants import OPENSKY_URL
from opensky.utils import get_api, process_data, save_csv


def main() -> None:
    """Consulta la API, procesa los datos e informa cuántos aviones hay."""

    data = get_api(OPENSKY_URL)
    aviones = process_data(data)
    path = save_csv(aviones)
    print(f"Hay {len(aviones)} aviones cerca de Ezeiza. Guardados en {path}")
