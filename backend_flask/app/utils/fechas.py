"""Conversion de fechas a la zona horaria del sistema.

Vivia dentro de turnos_routes.py, pero el calendario de grupos necesita lo
mismo y copiar seis lineas a otro modulo dejaba dos definiciones que podian
divergir en silencio: si una arregla un caso de borde y la otra no, dos
endpoints devuelven la misma fecha distinta y el sintoma aparece en el
calendario, lejos de la causa.
"""

from datetime import datetime, timedelta, timezone

# Argentina no aplica horario de verano desde 2009, asi que un offset fijo
# alcanza y evita depender de la base de datos de zonas horarias del sistema.
TZ_ARG = timezone(timedelta(hours=-3))


def a_iso_arg(dt):
    """Devuelve `dt` como string ISO 8601 en hora argentina.

    Lo que no es un datetime pasa sin tocar: las filas traen columnas opcionales
    que pueden venir en NULL, y devolverlas tal cual es preferible a romper la
    respuesta entera por un campo vacio.

    Un datetime sin zona se interpreta como hora argentina, no como UTC. MySQL
    devuelve los DATETIME sin offset y estan guardados en hora local; asumir UTC
    correria todo tres horas.
    """
    if not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_ARG)
    else:
        dt = dt.astimezone(TZ_ARG)
    return dt.isoformat()
