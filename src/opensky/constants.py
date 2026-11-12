"""Constantes del proyecto: URL de la API y zona alrededor de Ezeiza."""

OPENSKY_URL = "https://opensky-network.org/api/states/all"

EZE_LAT_MIN = -35
EZE_LAT_MAX = -34
EZE_LON_MIN = -59
EZE_LON_MAX = -58

TRIES = 3
INITIAL_WAIT = 1

API_RESPONSE_EXAMPLE = {
    "time": 1789000000,  # epoch del snapshot
    "states": [  # lista de aviones
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
